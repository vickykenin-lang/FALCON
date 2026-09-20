"""Falcon Bedrock Runtime authorization probe.
Separates bearer authentication, control-plane, native Runtime SDK, direct HTTP,
and OpenAI-compatible Runtime endpoint behavior. Never prints the API key.
"""
import json, os, urllib.error, urllib.request
import boto3
from botocore.exceptions import ClientError

key=os.environ['BEDROCK_API_KEY']
os.environ['AWS_BEARER_TOKEN_BEDROCK']=key
region=os.environ.get('BEDROCK_RUNTIME_REGION','us-east-1')
rt=boto3.client('bedrock-runtime',region_name=region)
control=boto3.client('bedrock',region_name=region)
out={'credential_available':bool(key),'configured':True,'region':region,'source_implemented':True,'tests':[]}

def errinfo(e):
    if isinstance(e,ClientError):
        r=e.response or {}; er=r.get('Error',{}); meta=r.get('ResponseMetadata',{})
        return {'error_code':er.get('Code'),'error_message':er.get('Message'),'http_status':meta.get('HTTPStatusCode'),'request_id':meta.get('RequestId')}
    if isinstance(e,urllib.error.HTTPError):
        raw=e.read().decode('utf-8','replace')[:1000]
        try:
            data=json.loads(raw); msg=data.get('message') or data.get('Message') or raw; code=data.get('__type') or data.get('code') or data.get('type')
        except Exception:
            msg=raw; code='HTTPError'
        return {'error_code':code,'error_message':msg,'http_status':e.code,'request_id':e.headers.get('x-amzn-requestid') or e.headers.get('x-amzn-request-id')}
    return {'error_code':type(e).__name__,'error_message':str(e)}

def add(name,api,model,ok=False,output=False,detail=None,error=None):
    row={'name':name,'api':api,'model':model,'live_request_verified':ok,'real_output_verified':output,'test_passed':ok and output}
    if detail: row['detail']=detail
    if error: row.update(error)
    out['tests'].append(row); print(json.dumps(row))

def post_json(url,payload):
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),method='POST',headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    with urllib.request.urlopen(req,timeout=45) as resp:
        raw=resp.read().decode('utf-8','replace'); return resp.status,json.loads(raw),resp.headers

# 1. Standard Bedrock control plane.
try:
    r=control.list_foundation_models(); n=len(r.get('modelSummaries',[]))
    add('standard_bedrock_control','ListFoundationModels','-',True,n>0,{'model_count':n})
except Exception as e: add('standard_bedrock_control','ListFoundationModels','-',error=errinfo(e))

# 2. Native Runtime Converse via boto3.
converse_model=os.environ.get('RUNTIME_CONVERSE_MODEL','us.anthropic.claude-sonnet-4-6')
try:
    r=rt.converse(modelId=converse_model,messages=[{'role':'user','content':[{'text':'Return exactly FALCON_RUNTIME_CONVERSE_OK'}]}],inferenceConfig={'maxTokens':40,'temperature':0})
    text=''.join(x.get('text','') for x in r.get('output',{}).get('message',{}).get('content',[]) if 'text' in x)
    add('runtime_converse_sdk','Converse',converse_model,True,bool(text),{'output_preview':text[:160],'match':'FALCON_RUNTIME_CONVERSE_OK' in text})
except Exception as e: add('runtime_converse_sdk','Converse',converse_model,error=errinfo(e))

# 3. Same Converse request as literal documented bearer HTTP request. This distinguishes SDK behavior from service behavior.
try:
    url=f'https://bedrock-runtime.{region}.amazonaws.com/model/{converse_model}/converse'
    status,data,headers=post_json(url,{'messages':[{'role':'user','content':[{'text':'Return exactly FALCON_DIRECT_HTTP_OK'}]}],'inferenceConfig':{'maxTokens':40,'temperature':0}})
    content=data.get('output',{}).get('message',{}).get('content',[]); text=''.join(x.get('text','') for x in content if isinstance(x,dict))
    add('runtime_converse_direct_http','Converse HTTP',converse_model,status==200,bool(text),{'output_preview':text[:160],'match':'FALCON_DIRECT_HTTP_OK' in text})
except Exception as e: add('runtime_converse_direct_http','Converse HTTP',converse_model,error=errinfo(e))

# 4. Amazon-owned Titan InvokeModel.
try:
    model='amazon.titan-embed-text-v2:0'
    r=rt.invoke_model(modelId=model,body=json.dumps({'inputText':'Falcon runtime authorization probe','dimensions':256,'normalize':True}),accept='application/json',contentType='application/json')
    data=json.loads(r['body'].read()); vec=data.get('embedding') or []
    add('runtime_invoke_embedding','InvokeModel',model,True,bool(vec),{'dimensions':len(vec)})
except Exception as e: add('runtime_invoke_embedding','InvokeModel','amazon.titan-embed-text-v2:0',error=errinfo(e))

# 5. Runtime OpenAI-compatible endpoint. Current AWS docs expose this on bedrock-runtime as well as Mantle.
# Failure/success tells us whether the restriction is native Invoke/Converse-specific or all runtime inference.
openai_model=os.environ.get('RUNTIME_OPENAI_MODEL','openai.gpt-oss-20b-1:0')
try:
    url=f'https://bedrock-runtime.{region}.amazonaws.com/openai/v1/chat/completions'
    status,data,headers=post_json(url,{'model':openai_model,'messages':[{'role':'user','content':'Return exactly FALCON_OPENAI_RUNTIME_OK'}],'max_tokens':40,'temperature':0})
    choices=data.get('choices') or []; text=((choices[0].get('message') or {}).get('content') if choices else '') or ''
    add('runtime_openai_chat_http','OpenAI Chat Completions HTTP',openai_model,status==200,bool(text),{'output_preview':text[:160],'match':'FALCON_OPENAI_RUNTIME_OK' in text})
except Exception as e: add('runtime_openai_chat_http','OpenAI Chat Completions HTTP',openai_model,error=errinfo(e))

out['summary']={'passed':sum(1 for x in out['tests'] if x['test_passed']),'total':len(out['tests'])}
with open('bedrock-runtime-probe.json','w',encoding='utf-8') as f: json.dump(out,f,indent=2)
