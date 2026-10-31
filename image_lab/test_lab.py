#!/usr/bin/env python3
"""Integration checks against the running local image lab."""
import base64,json,urllib.request,urllib.error
from pathlib import Path
BASE='http://127.0.0.1:8001'
def request(path,body=None,origin=None):
 headers={'Content-Type':'application/json'}
 if origin:headers['Origin']=origin
 req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
 try:
  with urllib.request.urlopen(req)as response:return response.status,response.read()
 except urllib.error.HTTPError as e:return e.code,e.read()
def main():
 status,data=request('/api/status');assert status==200 and json.loads(data)['ready']
 _,data=request('/api/gallery?limit=1000');rows=json.loads(data)['images'];assert len(rows)==60
 row=rows[0];assert request(row['image'])[0]==200
 status,data=request('/api/search',{'gallery_id':row['id'],'k':7});result=json.loads(data)
 assert status==200 and len(result['results'])==7 and row['id']not in[r['id']for r in result['results']]
 scores=[r['score']for r in result['results']];assert scores==sorted(scores,reverse=True)
 status,data=request('/api/search',{'gallery_id':row['id'],'k':1,'mode':'plain','exclude_self':False})
 assert status==200 and json.loads(data)['results'][0]['id']==row['id']
 file=Path(__file__).parent/'data/images'/Path(row['image']).name
 status,data=request('/api/search',{'image':base64.b64encode(file.read_bytes()).decode(),'k':3})
 assert status==200 and len(json.loads(data)['results'])==3
 for bad in ([],{'k':0},{'k':51},{'k':True},{'image':'not base64'},{'gallery_id':'missing'},{'mode':'bad'}):
  assert request('/api/search',bad)[0]==400,bad
 assert request('/api/search',{'gallery_id':row['id']},'https://example.com')[0]==403
 assert request('/images/../../.env')[0]==404
 assert request('/data/manifest.json')[0]==404
 print('PASS: gallery limit, image serving, sorted top-k, self exclusion/retrieval, upload, 7 invalid queries, origin and path controls.')
if __name__=='__main__':main()
