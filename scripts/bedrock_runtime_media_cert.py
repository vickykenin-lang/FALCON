"""Falcon Bedrock Runtime capability certification.
Uses the same Bedrock bearer API key via AWS_BEARER_TOKEN_BEDROCK.
No secret values are printed. Tests image generation + editing and text embeddings.
Video is reported separately because Nova Reel requires an S3 output bucket.
"""
import base64, io, json, os, sys
import boto3
from PIL import Image, ImageDraw

KEY=os.environ['BEDROCK_API_KEY']
os.environ['AWS_BEARER_TOKEN_BEDROCK']=KEY
REGION=os.environ.get('BEDROCK_RUNTIME_REGION','us-east-1')
client=boto3.client('bedrock-runtime', region_name=REGION)
ev={'credential_available':True,'configured':True,'region':REGION,'source_implemented':True,'tests':[]}

def add(capability, model, passed=False, live=False, output=False, detail='', error=''):
    row={'capability':capability,'model':model,'test_passed':passed,'live_request_verified':live,'real_output_verified':output}
    if detail: row['detail']=detail
    if error: row['error']=error[:1000]
    ev['tests'].append(row); print(json.dumps(row))

def invoke(model, body):
    r=client.invoke_model(modelId=model,body=json.dumps(body),accept='application/json',contentType='application/json')
    return json.loads(r['body'].read())

# 1. Text embeddings: semantic vector exists and has documented dimension.
try:
    model='amazon.titan-embed-text-v2:0'
    data=invoke(model,{'inputText':'Falcon durable memory semantic retrieval','dimensions':1024,'normalize':True})
    vec=data.get('embedding') or data.get('embeddingsByType',{}).get('float') or []
    add('text_embeddings',model,len(vec)==1024,True,bool(vec),f'dimensions={len(vec)} token_count={data.get("inputTextTokenCount")}')
except Exception as e: add('text_embeddings','amazon.titan-embed-text-v2:0',error=f'{type(e).__name__}: {e}')

# 2. Nova Canvas text-to-image.
try:
    model='amazon.nova-canvas-v1:0'
    data=invoke(model,{'taskType':'TEXT_IMAGE','textToImageParams':{'text':'A simple blue triangle centered on a clean white background, flat geometric icon'},'imageGenerationConfig':{'numberOfImages':1,'quality':'standard','height':512,'width':512,'cfgScale':6.5,'seed':17}})
    imgs=data.get('images') or []
    raw=base64.b64decode(imgs[0]) if imgs else b''
    ok=raw.startswith(b'\x89PNG') or raw.startswith(b'\xff\xd8\xff')
    add('image_generation',model,ok,True,bool(raw),f'bytes={len(raw)}')
except Exception as e: add('image_generation','amazon.nova-canvas-v1:0',error=f'{type(e).__name__}: {e}')

# 3. Nova Canvas image variation/edit path with deterministic local source image.
try:
    model='amazon.nova-canvas-v1:0'
    im=Image.new('RGB',(512,512),'white'); d=ImageDraw.Draw(im); d.rectangle((130,130,382,382),fill='red')
    b=io.BytesIO(); im.save(b,format='PNG'); src=base64.b64encode(b.getvalue()).decode()
    data=invoke(model,{'taskType':'IMAGE_VARIATION','imageVariationParams':{'images':[src],'text':'Transform the red square into a polished blue geometric icon on a white background','similarityStrength':0.7},'imageGenerationConfig':{'numberOfImages':1,'quality':'standard','height':512,'width':512,'cfgScale':6.5,'seed':19}})
    imgs=data.get('images') or []; raw=base64.b64decode(imgs[0]) if imgs else b''
    ok=raw.startswith(b'\x89PNG') or raw.startswith(b'\xff\xd8\xff')
    add('image_editing',model,ok,True,bool(raw),f'bytes={len(raw)}')
except Exception as e: add('image_editing','amazon.nova-canvas-v1:0',error=f'{type(e).__name__}: {e}')

# Nova Reel cannot be truthfully live-tested without an S3 output URI.
ev['video']={'model':'amazon.nova-reel-v1:1','source_implemented':False,'test_passed':False,'deployed':False,'live_request_verified':False,'real_output_verified':False,'blocker':'S3 output URI and s3:PutObject permission required for StartAsyncInvoke'}
ev['test_passed_count']=sum(1 for x in ev['tests'] if x['test_passed'])
with open('bedrock-runtime-media-cert.json','w') as f: json.dump(ev,f,indent=2)
# Do not fail entire diagnostic; evidence determines state.
