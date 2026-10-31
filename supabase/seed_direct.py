"""Explicit development fixtures for Supabase Auth (known passwords, no confirmation emails).
Uses the server-only DB URI to provision only the six requested test identities.
Never overwrites existing Auth users or their passwords.
"""
import os,sys,json,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'backend'))
from config import load_env
load_env()
import psycopg
SEEDS=[('maya','Maya',28,'Product designer'),('theo','Theo',31,'Pastry chef'),('priya','Priya',29,'Urban planner'),('jonah','Jonah',33,'Nurse'),('lena','Lena',30,'Architect'),('marcus','Marcus',32,'Music teacher')]

def main():
 with psycopg.connect(os.environ['HINGE_DATABASE_URL']) as db:
  for key,name,age,job in SEEDS:
   email=key+'@hinge.test'
   if db.execute('select 1 from auth.users where email=%s',(email,)).fetchone():continue
   uid=str(uuid.uuid4())
   db.execute('''insert into auth.users(instance_id,id,aud,role,email,encrypted_password,email_confirmed_at,
    raw_app_meta_data,raw_user_meta_data,created_at,updated_at,confirmation_token,recovery_token,email_change,email_change_token_new,email_change_token_current,reauthentication_token)
    values('00000000-0000-0000-0000-000000000000',%s,'authenticated','authenticated',%s,
    extensions.crypt(%s,extensions.gen_salt('bf')),now(),%s::jsonb,%s::jsonb,now(),now(),'','','','','','')''',
    (uid,email,'HingeTest2026!',json.dumps({'provider':'email','providers':['email']}),json.dumps({'name':name,'age':age})))
   db.execute('''insert into auth.identities(id,user_id,provider_id,identity_data,provider,created_at,updated_at)
    values(%s,%s,%s,%s::jsonb,'email',now(),now())''',
    (str(uuid.uuid4()),uid,uid,json.dumps({'sub':uid,'email':email,'email_verified':True})))
   db.execute('update dating.profiles set job=%s where id=%s',(job,uid))
 print('Development Auth fixtures ready; existing accounts were left unchanged.')
 from direct_api import Client, ROOT
 for key,_,_,_ in SEEDS:
  client=Client().login(key+'@hinge.test','HingeTest2026!')
  if not client.app()['me']['photos']:
   file=ROOT/f'ios/HingeMini/Assets.xcassets/{key}.imageset/{key}.jpg'
   if file.exists():client.upload(file.read_bytes())
 print('Bundled illustrative photos added to development accounts that had none.')
if __name__=='__main__':main()
