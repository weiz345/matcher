#!/usr/bin/env python3
"""Download a synthetic research gallery and a general CLIP image encoder.
No real-person scraping, demographic inference, or Supabase access.
"""
import argparse,hashlib,json,time,urllib.request,zipfile
from pathlib import Path
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
SOURCES={
 'sample4':('small-sample-4.zip','be0324f115b1eca4522d362c63297cf4d687e71bc0fd826de69d6cb64edc19ff'),
 'sample':('small-sample.zip','6fc49b4492fcf262e8e0165acf32ae9f62fd8fc89139dadabd058e41bc4281fc')}

def download(url,path,expected=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists()and(not expected or hashlib.sha256(path.read_bytes()).hexdigest()==expected):return
 temporary=path.with_suffix(path.suffix+'.part')
 for attempt in range(3):
  try:
   digest=hashlib.sha256();size=0;last=0
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'HingeMini-ResearchLab/1.0'}),timeout=60)as response,temporary.open('wb')as output:
    while True:
     chunk=response.read(1024*1024)
     if not chunk:break
     output.write(chunk);digest.update(chunk);size+=len(chunk)
     if size-last>=20*1024*1024:print(f'{path.name}: {size//(1024*1024)} MB',flush=True);last=size
   if expected and digest.hexdigest()!=expected:raise ValueError('Download checksum mismatch')
   temporary.replace(path);print(f'Downloaded {path.name}: {size:,} bytes',flush=True);return
  except Exception:
   temporary.unlink(missing_ok=True)
   if attempt==2:raise
   time.sleep(1)

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--limit',type=int,default=2000);parser.add_argument('--sample',choices=SOURCES,default='sample4');parser.add_argument('--append',action='store_true')
 args=parser.parse_args()
 if not 1<=args.limit<=10000:raise SystemExit('Use --limit between 1 and 10000')
 archive_name,checksum=SOURCES[args.sample]
 archive=DATA/'downloads'/archive_name
 download('https://huggingface.co/datasets/bitmind/SyntheticFacesHQ/resolve/main/'+archive_name,archive,checksum)
 output=DATA/'images';output.mkdir(parents=True,exist_ok=True)
 old=json.loads((DATA/'manifest.json').read_text())if args.append and(DATA/'manifest.json').exists()else None
 records=old['images'][:]if old else[]
 existing_ids={r['id']for r in records}
 with zipfile.ZipFile(archive)as z:
  names=sorted(n for n in z.namelist()if Path(n).suffix.lower()in('.jpg','.jpeg','.png','.webp')and not n.startswith('__MACOSX/'))
  for name in names[:args.limit]:
   identifier='s'+hashlib.sha256((archive_name+':'+name).encode()).hexdigest()[:14]
   file=output/(identifier+'.jpg')
   if not file.exists():
    with z.open(name)as stream,Image.open(stream)as im:
     im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((448,448));im.save(file,'JPEG',quality=90)
   if identifier not in existing_ids:records.append({'id':identifier,'file':file.name,'source_member':name,'source_archive':archive_name,'synthetic':True,'labels':{}})
  available=len(names)
 manifest={'source':'SFHQ synthetic faces, part 4 sample','source_url':'https://github.com/SelfishGene/SFHQ-dataset',
  'mirror':'https://huggingface.co/datasets/bitmind/SyntheticFacesHQ','archive':archive_name,'archive_sha256':checksum,
  'available_in_archive':available,'archives':list(dict.fromkeys((old.get('archives',[old['archive']])if old else[])+[archive_name])),'count':len(records),'labels':'No demographic, BMI, body-frame, or identity labels supplied.','images':records}
 (DATA/'manifest.json').write_text(json.dumps(manifest,indent=2))
 download('https://raw.githubusercontent.com/SelfishGene/SFHQ-dataset/main/LICENSE',DATA/'SFHQ-LICENSE.txt')
 download('https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/main/onnx/vision_model_quantized.onnx',DATA/'model'/'vision_model_quantized.onnx')
 download('https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/main/preprocessor_config.json',DATA/'model'/'preprocessor_config.json')
 print(f'Ready: {len(records)} synthetic images ({available} available in this archive). Model and provenance saved.',flush=True)
if __name__=='__main__':main()
