"""Real Supabase Auth/REST/Storage and RLS integration tests against disposable users."""
import unittest,uuid,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from direct_api import Client,RequestError,ROOT
from test_fixtures import Fixtures
import psycopg

class DirectTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.fixture=Fixtures(3);cls.clients=[];cls.objects=[]
  try:
   for person in cls.fixture.identities:cls.clients.append(Client().login(person['email'],cls.fixture.password))
   cls.a,cls.b,cls.c=cls.clients
  except Exception:cls.fixture.cleanup();raise
 @classmethod
 def tearDownClass(cls):
  for client,path in cls.objects:
   try:client.remove_object(path)
   except Exception:pass
  cls.fixture.cleanup()
 def assert_denied(self,fn):
  with self.assertRaises(RequestError)as result:fn()
  self.assertIn(result.exception.status,[400,401,403,404])
 def test_01_anonymous_and_owned_profile(self):
  self.assert_denied(lambda:Client().app())
  own=self.a.app()['me'];other=self.b.app()['me'];own['name']='Alice Updated'
  own['prompts'][0]['id']=other['prompts'][0]['id'];own['prompts'][0]['answer']='<script>text only</script>'
  result=self.a.action('profile',own)['app']['me']
  self.assertEqual(result['name'],'Alice Updated')
  self.assertNotEqual(result['prompts'][0]['id'],other['prompts'][0]['id'])
  self.assertNotEqual(self.b.app()['me']['prompts'][0]['answer'],'<script>text only</script>')
 def test_02_private_storage_and_item_ownership(self):
  data=(ROOT/'ios/HingeMini/Assets.xcassets/coffee.imageset/coffee.jpg').read_bytes()
  pid,path=self.b.upload(data);self.objects.append((self.b,path));self.__class__.photo_id=pid;self.__class__.photo_path=path
  self.assertEqual(self.a.photo(pid),data)
  self.assert_denied(lambda:Client().request('/storage/v1/object/authenticated/dating-photos/'+path))
  self.assert_denied(lambda:self.a.action('photo_delete',{'id':pid}))
  self.assert_denied(lambda:self.a.request('/storage/v1/object/dating-photos/'+path,b'bad',binary=True,mime='text/html'))
  mine=self.a.app()['me'];other=self.b.app()['me']
  self.assert_denied(lambda:self.a.action('like',{'target':other['id'],'itemType':'prompt','itemID':mine['prompts'][0]['id']}))
 def test_03_mutual_match_and_conversation_controls(self):
  other=self.b.app()['me'];mine=self.a.app()['me']
  result=self.a.action('like',{'target':other['id'],'itemType':'photo','itemID':self.photo_id,'comment':'Coffee?'})
  self.assertIsNone(result['matchID'])
  incoming=self.b.app()['likes'];self.assertTrue(any(l['comment']=='Coffee?'and l['person']['id']==mine['id']for l in incoming))
  result=self.b.action('accept',{'target':mine['id']});cid=result['matchID'];self.assertTrue(cid);self.__class__.cid=cid
  self.assertEqual(self.b.action('accept',{'target':mine['id']})['matchID'],cid)
  self.assert_denied(lambda:self.c.rpc('dating_messages',{'p_conversation':cid}))
  self.assert_denied(lambda:self.c.action('message',{'conversation':cid,'text':'Unauthorized','clientID':'x'}))
  self.assert_denied(lambda:self.c.action('unmatch',{'conversation':cid}))
 def test_04_messages_idempotent_and_real_senders(self):
  cid=self.cid;body={'conversation':cid,'text':'Hello from Alice','clientID':str(uuid.uuid4()),'sender':self.c.app()['me']['id']}
  self.a.action('message',body);self.a.action('message',body)
  received=self.b.rpc('dating_messages',{'p_conversation':cid})['messages'];self.assertEqual(len(received),1)
  self.assertFalse(received[0]['mine']);self.assertEqual(received[0]['senderID'],self.a.app()['me']['id'])
  self.b.action('message',{'conversation':cid,'text':'Hi from Bob','clientID':str(uuid.uuid4())})
  self.assertEqual([m['mine']for m in self.a.rpc('dating_messages',{'p_conversation':cid})['messages']],[True,False])
  self.assert_denied(lambda:self.a.action('message',{'conversation':cid,'text':'','clientID':'empty'}))
 def test_05_rls_without_rpc_bypass(self):
  with psycopg.connect(self.fixture.target)as db:
   db.execute('set local role authenticated')
   db.execute("select set_config('request.jwt.claims',%s,true)",(__import__('json').dumps({'sub':self.fixture.identities[2]['id'],'role':'authenticated'}),))
   self.assertEqual(db.execute('select count(*)from dating.messages where conversation_id=%s',(self.cid,)).fetchone()[0],0)
   with self.assertRaises(psycopg.Error):db.execute('update dating.conversations set active=false where id=%s',(self.cid,))
 def test_06_unmatch_and_block(self):
  self.a.action('unmatch',{'conversation':self.cid})
  for client in [self.a,self.b]:
   self.assert_denied(lambda:client.rpc('dating_messages',{'p_conversation':self.cid}))
   self.assert_denied(lambda:client.action('message',{'conversation':self.cid,'text':'after unmatch','clientID':'ended'}))
  self.assert_denied(lambda:self.b.action('accept',{'target':self.a.app()['me']['id']}))
  self.a.action('block',{'target':self.b.app()['me']['id']})
  self.assert_denied(lambda:self.a.photo(self.photo_id))
  self.assert_denied(lambda:self.a.request('/storage/v1/object/authenticated/dating-photos/'+self.photo_path))
  self.assert_denied(lambda:self.b.action('like',{'target':self.a.app()['me']['id'],'itemType':'prompt','itemID':self.a.app()['me']['prompts'][0]['id']}))
  self.assertFalse(any(p['id']==self.b.app()['me']['id']for p in self.a.app()['discover']))
 def test_07_refresh_and_logout(self):
  refresh=self.c.session['refresh_token']
  session=self.c.request('/auth/v1/token?grant_type=refresh_token',{'refresh_token':refresh},auth=False)
  self.assertTrue(session['access_token']);self.c.session=session
  self.c.request('/auth/v1/logout?scope=local',{},auth=True)
  self.assert_denied(lambda:self.c.request('/auth/v1/token?grant_type=refresh_token',{'refresh_token':session['refresh_token']},auth=False))

if __name__=='__main__':unittest.main(verbosity=2)
