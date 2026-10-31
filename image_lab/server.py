#!/usr/bin/env python3
"""Local visual-similarity sandbox. Separate from the dating app and Supabase."""
import argparse,base64,io,json,mimetypes,re,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from PIL import Image,ImageOps
from engine import DATA,ROOT,Gallery

class State:
 def __init__(self):self.gallery=None;self.lock=threading.Lock();self.manifest=None
 def manifest_data(self):
  self.manifest=json.loads((DATA/'manifest.json').read_text());return self.manifest
 def engine(self):
  with self.lock:
   if self.gallery is None:self.gallery=Gallery()
   return self.gallery
STATE=State()

def transform_image(im,name):
 if name=='flip':return ImageOps.mirror(im)
 if name=='crop':
  side=int(min(im.size)*.8);x=(im.width-side)//2;y=(im.height-side)//2;return im.crop((x,y,x+side,y+side))
 if name=='rotate':return im.rotate(12,resample=Image.Resampling.BICUBIC,expand=False,fillcolor=(128,128,128))
 return im

class Handler(BaseHTTPRequestHandler):
 def reply(self,status,data,mime='application/json'):
  if mime=='application/json':data=json.dumps(data).encode()
  self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
  try:self.wfile.write(data)
  except(BrokenPipeError,ConnectionResetError):pass
 def do_GET(self):
  uri=urlsplit(self.path);q=parse_qs(uri.query)
  try:
   if uri.path=='/api/status':
    manifest=STATE.manifest_data();progress=json.loads((DATA/'progress.json').read_text())if(DATA/'progress.json').exists()else{}
    return self.reply(200,{'count':manifest['count'],'ready':(DATA/'index.npz').exists()and progress.get('ready',False),'progress':progress,'source':manifest['source'],'archives':manifest.get('archives',[manifest['archive']]),'model':'CLIP ViT-B/32, quantized, general visual features','demographic_labels':False})
   if uri.path=='/api/gallery':
    rows=STATE.manifest_data()['images'];offset=max(0,int(q.get('offset',['0'])[0]));limit=min(60,max(1,int(q.get('limit',['24'])[0])))
    return self.reply(200,{'images':[{'id':r['id'],'image':'/images/'+r['file']}for r in rows[offset:offset+limit]],'total':len(rows)})
   if uri.path=='/api/evaluation':
    return self.reply(200,json.loads((DATA/'evaluation.json').read_text())if(DATA/'evaluation.json').exists()else{'runs':[]})
   if re.fullmatch(r'/images/s[0-9a-f]{14}\.jpg',uri.path):
    file=DATA/'images'/Path(uri.path).name
    if file.is_file():return self.reply(200,file.read_bytes(),'image/jpeg')
   static={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
   if uri.path in static:
    file=ROOT/'web'/static[uri.path];return self.reply(200,file.read_bytes(),mimetypes.guess_type(file.name)[0]or'text/plain')
   return self.reply(404,{'error':'Not found'})
  except(ValueError,FileNotFoundError):return self.reply(503,{'error':'Gallery/index not ready; run download_dataset.py and build_index.py.'})
 def do_POST(self):
  if self.path!='/api/search':return self.reply(404,{'error':'Not found'})
  origin=self.headers.get('Origin')
  if origin and urlsplit(origin).netloc!=self.headers.get('Host'):return self.reply(403,{'error':'Origin not allowed'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=8*1024*1024:raise ValueError('Query must be at most 8 MB')
   if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Expected JSON')
   body=json.loads(self.rfile.read(length))
   if not isinstance(body,dict):raise ValueError('Expected a JSON object')
   k=body.get('k',12);mode=body.get('mode','robust');transform=body.get('transform','original')
   if type(k)is not int or not 1<=k<=50:raise ValueError('Top k must be between 1 and 50')
   if mode not in('plain','robust')or transform not in('original','flip','crop','rotate'):raise ValueError('Unknown search option')
   engine=STATE.engine();identifier=body.get('gallery_id');start=time.perf_counter()
   if identifier:
    if identifier not in engine.by_id:raise ValueError('Unknown gallery image')
    im=Image.open(DATA/'images'/engine.by_id[identifier]['file'])
   else:
    encoded=body.get('image','')
    if not isinstance(encoded,str):raise ValueError('Choose an image')
    if ','in encoded:encoded=encoded.split(',',1)[1]
    im=Image.open(io.BytesIO(base64.b64decode(encoded,validate=True)))
   with im:
    if max(im.size)/min(im.size)>10:raise ValueError('Choose an image with aspect ratio below 10:1')
    if im.width*im.height>20_000_000:raise ValueError('Choose an image smaller than 20 megapixels')
    im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((1600,1600));im=transform_image(im,transform)
    exclude=identifier if body.get('exclude_self',True)else None
    results=engine.search(im,k,mode,exclude)
    im.thumbnail((360,360));preview=io.BytesIO();im.save(preview,'JPEG',quality=88)
   self.reply(200,{'results':results,'elapsed_ms':round((time.perf_counter()-start)*1000),'mode':mode,'transform':transform,
     'preview':'data:image/jpeg;base64,'+base64.b64encode(preview.getvalue()).decode(),'count':len(engine.ids)})
  except Exception as e:
   if isinstance(e,(ValueError,TypeError,OSError,KeyError)):return self.reply(400,{'error':str(e)[:180]})
   self.log_error('Search failed: %s',type(e).__name__);return self.reply(503,{'error':'Search unavailable. Build the gallery index first.'})

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',default='0.0.0.0');p.add_argument('--port',type=int,default=8001);a=p.parse_args()
 print(f'Image lab: http://{a.host}:{a.port} (synthetic gallery; uploaded queries stay in request memory)',flush=True)
 ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
