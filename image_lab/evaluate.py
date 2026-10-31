#!/usr/bin/env python3
"""Same-image perturbation checks, not a test of real pose/identity invariance."""
import base64,io,json
from PIL import Image
from engine import DATA,Gallery
from server import transform_image

def main():
 gallery=Gallery();runs=[]
 for offset in (0,len(gallery.rows)//2,len(gallery.rows)-1):
  row=gallery.rows[offset];tests=[];examples=[]
  with Image.open(DATA/'images'/row['file']) as source:
   source=source.convert('RGB')
   for transform in ('original','flip','crop','rotate'):
    query=transform_image(source,transform);ranks={}
    for mode in ('plain','robust'):
     results=gallery.search(query,50,mode)
     ranks[mode]=next((i+1 for i,r in enumerate(results)if r['id']==row['id']),None)
     assert all(results[i]['score']>=results[i+1]['score']for i in range(len(results)-1))
     assert len({r['id']for r in results})==50
    tests.append({'transform':transform,'plain_rank':ranks['plain'],'robust_rank':ranks['robust']})
    if transform!='original':
     preview=query.copy();preview.thumbnail((240,240));buffer=io.BytesIO();preview.save(buffer,'JPEG',quality=80)
     examples.append({'transform':transform,'self_rank':ranks['robust'],'preview':'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode()})
   assert gallery.search(source,1,'plain')[0]['id']==row['id']
   assert row['id']not in[r['id']for r in gallery.search(source,12,'robust',row['id'])]
  runs.append({'id':row['id'],'label':f'Synthetic reference {len(runs)+1}','tests':tests,'examples':examples})
 report={'scope':'Three references, same-image transforms only; no true camera-angle, demographic or identity validation.','runs':runs}
 (DATA/'evaluation.json').write_text(json.dumps(report))
 print(json.dumps([{ 'id':r['id'],'tests':r['tests']}for r in runs],indent=2))
if __name__=='__main__':main()
