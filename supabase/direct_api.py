"""Small test/setup client using only public Supabase endpoints and user JWTs."""
import json,re,urllib.request,urllib.error,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
config=(ROOT/'supabase-config.js').read_text()
URL=re.search(r"SUPABASE_URL = '([^']+)'",config)[1]
KEY=re.search(r"SUPABASE_PUBLISHABLE_KEY = '([^']+)'",config)[1]

class RequestError(Exception):
 def __init__(self,status,message):self.status=status;super().__init__(message)

class Client:
 def __init__(self):self.session=None
 def request(self,path,body=None,method=None,binary=False,mime='application/json',auth=True):
  headers={'apikey':KEY}
  if auth and self.session:headers['Authorization']='Bearer '+self.session['access_token']
  if body is not None:headers['Content-Type']=mime
  if binary:headers['Cache-Control']='max-age=0'
  data=body if binary else json.dumps(body).encode() if body is not None else None
  req=urllib.request.Request(URL+path,data=data,headers=headers,method=method or('POST'if body is not None else'GET'))
  try:
   with urllib.request.urlopen(req,timeout=30)as r:
    value=r.read()
    return json.loads(value)if'application/json'in r.headers.get('Content-Type','')else value
  except urllib.error.HTTPError as e:
   try:value=json.loads(e.read())
   except ValueError:value={}
   raise RequestError(e.code,value.get('message')or value.get('msg')or value.get('error_description')or'Supabase request failed')from None
 def login(self,email,password):
  self.session=self.request('/auth/v1/token?grant_type=password',{'email':email,'password':password},auth=False);return self
 def rpc(self,name,body=None):return self.request('/rest/v1/rpc/'+name,body or{})
 def app(self):return self.rpc('dating_bootstrap')
 def action(self,name,body=None):return self.rpc('dating_action',{'p_action':name,'p_body':body or{}})
 def upload(self,data):
  pid=str(uuid.uuid4());path=self.session['user']['id']+'/'+pid
  self.request('/storage/v1/object/dating-photos/'+path,data,binary=True,mime='image/jpeg')
  try:self.action('photo_register',{'id':pid,'mime':'image/jpeg'})
  except Exception:
   self.remove_object(path);raise
  return pid,path
 def remove_object(self,path):return self.request('/storage/v1/object/dating-photos',{'prefixes':[path]},method='DELETE')
 def photo(self,pid):
  info=self.rpc('dating_photo',{'p_id':pid})
  return self.request('/storage/v1/object/authenticated/dating-photos/'+info['path'])
