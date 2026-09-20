"""Falcon Bedrock Runtime authorization probe.
Separates bearer authentication, Converse, InvokeModel and model-specific failures.
Never prints the Bedrock API key.
"""
import json, os
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
    return {'error_code':type(e).__name__,'error_message':str(e)}

def add(name,api,model,ok=False,output=False,detail=None,error=None):
    row={'name':name,'api':api,'model':model,'live_request_verified':ok,'real_output_verified':output,'test_passed':ok and output}
    if detail: row['detail']=detail
    if error: row.update(error)
    out['tests'].append(row); print(json.dumps(row))

# Control-plane proof: confirms bearer key can call standard Bedrock endpoint, not Mantle only.
try:
    r=control.list_foundation_models()
    n=len(r.get('modelSummaries',[])); add('standard_bedrock_control','ListFoundationModels','-',True,n>0,{'model_count':n})
except Exception as e: add('standard_bedrock_control','ListFoundationModels','-',error=errinfo(e))

# Runtime Converse using an AWS-documented inference-profile style model ID.
# Failure is diagnostic and does not imply Claude entitlement is expected to pass.
try:
    model=os.environ.get('RUNTIME_CONVERSE_MODEL','us.anthropic.claude-sonnet-4-6')
    r=rt.converse(modelId=model,messages=[{'role':'user','content':[{'text':'Return exactly FALCON_RUNTIME_CONVERSE_OK'}]}],inferenceConfig={'maxTokens':40,'temperature':0})
    text=''.join(x.get('text','') for x in r.get('output',{}).get('message',{}).get('content',[]) if 'text' in x)
    add('runtime_converse','Converse',model,True,bool(text),{'output_preview':text[:160],'match':'FALCON_RUNTIME_CONVERSE_OK' in text})
except Exception as e: add('runtime_converse','Converse',os.environ.get('RUNTIME_CONVERSE_MODEL','us.anthropic.claude-sonnet-4-6'),error=errinfo(e))

# InvokeModel: Titan embedding is Amazon-owned and removes third-party entitlement from the equation.
try:
    model='amazon.titan-embed-text-v2:0'
    r=rt.invoke_model(modelId=model,body=json.dumps({'inputText':'Falcon runtime authorization probe','dimensions':256,'normalize':True}),accept='application/json',contentType='application/json')
    data=json.loads(r['body'].read()); vec=data.get('embedding') or []
    add('runtime_invoke_embedding','InvokeModel',model,True,bool(vec),{'dimensions':len(vec)})
except Exception as e: add('runtime_invoke_embedding','InvokeModel','amazon.titan-embed-text-v2:0',error=errinfo(e))

out['summary']={'passed':sum(1 for x in out['tests'] if x['test_passed']),'total':len(out['tests'])}
with open('bedrock-runtime-probe.json','w',encoding='utf-8') as f: json.dump(out,f,indent=2)
