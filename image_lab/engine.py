"""General visual embeddings over a synthetic-only gallery; no identity/trait classifier."""
from pathlib import Path
import json,threading
import numpy as np
import onnxruntime as ort
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
VERSION='clip-vit-base-patch32-q8-center-flip-inner84-v1'
MEAN=np.array([.48145466,.4578275,.40821073],dtype=np.float32)[:,None,None]
STD=np.array([.26862954,.26130258,.27577711],dtype=np.float32)[:,None,None]

def normalized(value):
 value=np.asarray(value,dtype=np.float32)
 return value/np.maximum(np.linalg.norm(value,axis=-1,keepdims=True),1e-8)

def prepare(image):
 im=ImageOps.exif_transpose(image).convert('RGB')
 short=min(im.size);scale=224/short
 im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.BICUBIC)
 left=(im.width-224)//2;top=(im.height-224)//2
 value=np.asarray(im.crop((left,top,left+224,top+224)),dtype=np.float32).transpose(2,0,1)/255
 return (value-MEAN)/STD

def image_views(image):
 im=ImageOps.exif_transpose(image).convert('RGB')
 side=int(min(im.size)*.84);x=(im.width-side)//2;y=(im.height-side)//2
 return [im,ImageOps.mirror(im),im.crop((x,y,x+side,y+side))]

class Encoder:
 def __init__(self):
  options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
  self.session=ort.InferenceSession(str(DATA/'model/vision_model_quantized.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
  self.input=self.session.get_inputs()[0].name
  outputs=[v.name for v in self.session.get_outputs()]
  self.output='image_embeds'if'image_embeds'in outputs else outputs[0]
  self.lock=threading.Lock()
 def encode_many(self,images):
  batch=np.stack([prepare(image)for image in images])
  with self.lock:features=self.session.run([self.output],{self.input:batch})[0]
  if features.ndim!=2:raise RuntimeError('Unexpected embedding model output')
  return normalized(features)
 def encode(self,image,mode='robust'):
  values=self.encode_many(image_views(image)if mode=='robust'else[image])
  return normalized(values.mean(axis=0))

class Gallery:
 def __init__(self):
  self.manifest=json.loads((DATA/'manifest.json').read_text())
  self.rows=self.manifest['images'];self.by_id={r['id']:r for r in self.rows}
  self.encoder=Encoder()
  with np.load(DATA/'index.npz',allow_pickle=False)as index:
   self.ids=index['ids'].tolist();self.plain=index['plain'];self.robust=index['robust']
   if str(index['version'])!=VERSION:raise RuntimeError('Index version changed; rebuild it')
  if self.ids!=[r['id']for r in self.rows]:raise RuntimeError('Gallery changed; rebuild the index')
 def search(self,image,k=12,mode='robust',exclude=None):
  vector=self.encoder.encode(image,mode)
  matrix=self.robust if mode=='robust'else self.plain
  scores=matrix@vector
  if exclude in self.ids:scores[self.ids.index(exclude)]=-np.inf
  order=np.argsort(-scores,kind='stable')[:min(k,len(self.ids)-(1 if exclude in self.ids else 0))]
  return [{'id':self.ids[i],'score':round(float(scores[i]),6),'image':'/images/'+self.by_id[self.ids[i]]['file']}for i in order]
