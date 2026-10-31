#!/usr/bin/env python3
import json,time,datetime
import numpy as np
from PIL import Image
from engine import DATA,VERSION,Encoder,normalized,image_views

def write_progress(state):
 temporary=DATA/'progress.tmp.json'
 temporary.write_text(json.dumps(state));temporary.replace(DATA/'progress.json')

def main():
 manifest=json.loads((DATA/'manifest.json').read_text());rows=manifest['images'];ids=[r['id']for r in rows]
 start=time.monotonic();total=len(rows)
 state={'done':0,'total':total,'elapsed_seconds':0,'ready':False,'phase':'loading_model',
        'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'images_per_second':0,'eta_seconds':None}
 write_progress(state)
 encoder=Encoder();plain=[];robust=[]
 for offset in range(0,total,8):
  batch=[]
  for row in rows[offset:offset+8]:
   with Image.open(DATA/'images'/row['file'])as im:batch.extend(image_views(im))
  values=encoder.encode_many(batch).reshape(-1,3,512)
  plain.extend(values[:,0]);robust.extend(normalized(values.mean(axis=1)))
  done=min(offset+8,total)
  elapsed=time.monotonic()-start;rate=done/max(elapsed,.001)
  state.update(done=done,elapsed_seconds=round(elapsed,1),images_per_second=round(rate,2),
               eta_seconds=round((total-done)/rate,1),phase='embedding')
  write_progress(state)
  if done%64==0 or done==total:print(f'Embedded {done}/{total} ({done/total:.0%}) · {elapsed:.1f}s elapsed · {rate:.1f} images/s · ~{state["eta_seconds"]:.0f}s remaining',flush=True)
 state.update(phase='saving',eta_seconds=None);write_progress(state)
 temporary=DATA/'index.tmp.npz'
 np.savez_compressed(temporary,ids=np.array(ids),plain=np.array(plain,dtype=np.float32),robust=np.array(robust,dtype=np.float32),version=np.array(VERSION))
 temporary.replace(DATA/'index.npz')
 state.update(ready=True,phase='complete',eta_seconds=0,elapsed_seconds=round(time.monotonic()-start,1));write_progress(state)
 print(f'Index saved. Total: {state["elapsed_seconds"]}s.',flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  if (DATA/'progress.json').exists():
   state=json.loads((DATA/'progress.json').read_text());state.update(ready=False,phase='failed',eta_seconds=None);write_progress(state)
  raise
