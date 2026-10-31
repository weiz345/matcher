"""Run: python3 -m unittest discover -s backend -v"""
import base64
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from server import Handler, make_server
from database import ROOT, connect

class QuietHandler(Handler):
    def log_message(self, *_): pass

class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'app.sqlite3'
        self.start()

    def start(self):
        self.server = make_server('127.0.0.1', 0, self.db)
        self.server.RequestHandlerClass = QuietHandler
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def tearDown(self):
        self.stop(); self.temp.cleanup()

    def request(self, method, path, body=None, token=None, origin=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        headers = {'Content-Type':'application/json'}
        if token: headers['Authorization'] = 'Bearer ' + token
        if origin: headers['Origin'] = origin
        c.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = c.getresponse(); status = response.status; data = response.read()
        cookie = response.getheader('Set-Cookie')
        if response.getheader('Content-Type') == 'application/json': data = json.loads(data)
        c.close(); return status, data, cookie

    def ok(self, method, path, body=None, token=None):
        status, data, _ = self.request(method,path,body,token)
        self.assertIn(status, (200,201),data); return data

    def login(self, name):
        return self.ok('POST','/api/login',dict(email=name+'@hinge.test',password='HingeTest2026!'))

    def pair(self):
        a,b = self.login('maya'),self.login('theo')
        pa,pb = a['app']['me'],b['app']['me']
        result = self.ok('POST','/api/likes',dict(target=pb['id'],itemType='prompt',itemID=pb['prompts'][0]['id'],comment='Coffee?'),a['token'])
        self.assertIsNone(result['matchID'])
        result = self.ok('POST',f"/api/likes/{pa['id']}/accept",{},b['token'])
        return a,b,result['matchID']

    def test_signup_passwords_sessions_and_logout(self):
        credentials=dict(email='new@example.com',password='StrongPassword12!',name='New',age=25)
        data=self.ok('POST','/api/signup',credentials)
        self.assertEqual(data['app']['me']['name'],'New')
        status,_,cookie=self.request('POST','/api/login',dict(email=credentials['email'],password=credentials['password']))
        self.assertEqual(status,200); self.assertIn('HttpOnly',cookie); self.assertIn('SameSite=Strict',cookie)
        self.assertEqual(self.request('POST','/api/signup',credentials)[0],409)
        self.assertEqual(self.request('POST','/api/login',dict(email=credentials['email'],password='wrong'))[0],401)
        self.assertEqual(self.request('GET','/api/app')[0],401)
        self.assertEqual(self.request('GET','/api/app',token='fake')[0],401)
        self.ok('POST','/api/logout',{},data['token'])
        self.assertEqual(self.request('GET','/api/app',token=data['token'])[0],401)
        with connect(self.db) as db:
            stored=db.execute('SELECT password_hash,salt FROM accounts WHERE email=?',(credentials['email'],)).fetchone()
        self.assertNotIn(credentials['password'],stored)
        self.assertEqual(len(stored[0]),64)

    def test_signup_validation(self):
        body=dict(email='user@example.com',password='Password1234',name='User',age=17)
        self.assertEqual(self.request('POST','/api/signup',body)[0],400)
        self.assertEqual(self.request('POST','/api/signup',{**body,'age':25,'password':'short'})[0],400)
        self.assertEqual(self.request('POST','/api/signup',{**body,'age':True})[0],400)

    def test_like_ownership_and_mutual_match(self):
        a,b=self.login('maya'),self.login('theo')
        pa,pb=a['app']['me'],b['app']['me']
        invalid=dict(target=pb['id'],itemType='prompt',itemID=pa['prompts'][0]['id'],comment='Hi')
        self.assertEqual(self.request('POST','/api/likes',invalid,a['token'])[0],400)
        valid={**invalid,'itemID':pb['prompts'][0]['id']}
        self.ok('POST','/api/likes',valid,a['token']);self.ok('POST','/api/likes',valid,a['token'])
        incoming=self.ok('GET','/api/app',token=b['token'])['likes']
        self.assertEqual(len(incoming),1);self.assertEqual(incoming[0]['comment'],'Hi')
        result=self.ok('POST',f"/api/likes/{pa['id']}/accept",{},b['token'])
        self.assertTrue(result['matchID']);self.assertEqual(len(result['app']['matches']),1)
        again=self.ok('POST',f"/api/likes/{pa['id']}/accept",{},b['token'])
        self.assertEqual(result['matchID'],again['matchID'])
        self.assertEqual(self.ok('GET','/api/app',token=a['token'])['likes'],[])

    def test_photo_likes_and_invalid_self_like(self):
        a,b=self.login('maya'),self.login('theo');p=b['app']['me']
        self.ok('POST','/api/likes',dict(target=p['id'],itemType='photo',itemID=p['photos'][0].split('/')[-1],comment='Great photo'),a['token'])
        incoming=self.ok('GET','/api/app',token=b['token'])['likes'][0]
        self.assertEqual(incoming['itemType'],'photo')
        self.assertEqual(self.request('POST','/api/likes',dict(target=p['id'],itemType='prompt',itemID=p['prompts'][0]['id']),b['token'])[0],404)

    def test_messages_delivered_and_never_scripted(self):
        a,b,cid=self.pair()
        payload=dict(text='Hello from Maya',clientID='test-message-1')
        self.ok('POST',f'/api/conversations/{cid}/messages',payload,a['token'])
        self.ok('POST',f'/api/conversations/{cid}/messages',payload,a['token'])
        received=self.ok('GET',f'/api/conversations/{cid}/messages',token=b['token'])['messages']
        self.assertEqual(len(received),1);self.assertFalse(received[0]['mine']);self.assertEqual(received[0]['text'],payload['text'])
        self.ok('POST',f'/api/conversations/{cid}/messages',dict(text='Hi from Theo',clientID='reply-1'),b['token'])
        received=self.ok('GET',f'/api/conversations/{cid}/messages',token=a['token'])['messages']
        self.assertEqual([m['mine'] for m in received],[True,False])
        self.assertEqual([m['text'] for m in received],['Hello from Maya','Hi from Theo'])

    def test_nonmember_and_unmatched_access(self):
        a,b,cid=self.pair();third=self.login('priya')
        for method in ['GET','POST']:
            body=dict(text='intrusion',clientID='bad') if method=='POST' else None
            self.assertEqual(self.request(method,f'/api/conversations/{cid}/messages',body,third['token'])[0],404)
        self.assertEqual(self.request('DELETE',f'/api/conversations/{cid}',token=third['token'])[0],404)
        self.ok('DELETE',f'/api/conversations/{cid}',token=a['token'])
        for user in [a,b]:
            self.assertEqual(self.ok('GET','/api/app',token=user['token'])['matches'],[])
            self.assertEqual(self.request('GET',f'/api/conversations/{cid}/messages',token=user['token'])[0],404)
            self.assertEqual(self.request('POST',f'/api/conversations/{cid}/messages',dict(text='after unmatch',clientID='bad'),user['token'])[0],404)
        self.assertEqual(self.request('POST',f"/api/likes/{a['app']['me']['id']}/accept",{},b['token'])[0],409)

    def test_block_revokes_both_sides(self):
        a,b,cid=self.pair();pa,pb=a['app']['me'],b['app']['me']
        self.ok('POST','/api/blocks',dict(target=pb['id']),a['token'])
        for user,other in [(a,pb),(b,pa)]:
            state=self.ok('GET','/api/app',token=user['token'])
            self.assertFalse(any(p['id']==other['id'] for p in state['discover']))
            self.assertEqual(state['matches'],[]);self.assertEqual(state['likes'],[])
            self.assertEqual(self.request('GET',other['photos'][0],token=user['token'])[0],404)
            self.assertEqual(self.request('POST','/api/likes',dict(target=other['id'],itemType='prompt',itemID=other['prompts'][0]['id']),user['token'])[0],404)
            self.assertEqual(self.request('GET',f'/api/conversations/{cid}/messages',token=user['token'])[0],404)

    def test_photo_profile_ownership_and_restart(self):
        a,b,cid=self.pair();p=a['app']['me'];p['name']='Updated Maya';p['prompts'][0]['answer']='<script>plain text</script>'
        self.ok('PUT','/api/profile',p,a['token'])
        data=(ROOT/'ios/HingeMini/Assets.xcassets/coffee.imageset/coffee.jpg').read_bytes()
        result=self.ok('POST','/api/photos',dict(data=base64.b64encode(data).decode()),a['token'])
        path='/api/photos/'+result['photoID']
        self.assertEqual(self.request('GET',path,token=b['token'])[1],data)
        self.assertEqual(self.request('DELETE',path,token=b['token'])[0],404)
        self.ok('POST',f'/api/conversations/{cid}/messages',dict(text='Persistent',clientID='restart'),a['token'])
        self.stop();self.start()
        restored=self.ok('GET','/api/app',token=a['token'])
        self.assertEqual(restored['me']['name'],'Updated Maya')
        self.assertEqual(restored['matches'][0]['messages'][0]['text'],'Persistent')
        self.assertIn(path,restored['me']['photos'])
        self.ok('DELETE',path,token=a['token'])
        self.assertEqual(self.request('GET',path,token=a['token'])[0],404)

    def test_history_pagination_and_invalid_messages(self):
        a,b,cid=self.pair()
        with connect(self.db) as db:
            db.executemany('INSERT INTO chat_messages(conversation_id,sender,text,created_at,client_id) VALUES (?,?,?,?,?)',
                           [(cid,a['app']['me']['id'],str(i),i,'m'+str(i)) for i in range(105)])
        recent=self.ok('GET',f'/api/conversations/{cid}/messages',token=b['token'])['messages']
        self.assertEqual(len(recent),100)
        old=self.ok('GET',f"/api/conversations/{cid}/messages?before={recent[0]['id']}",token=b['token'])['messages']
        self.assertEqual(len(old),5)
        for value in ['', ' ', 'x'*1001]:
            self.assertEqual(self.request('POST',f'/api/conversations/{cid}/messages',dict(text=value,clientID='invalid'),a['token'])[0],400)

    def test_reciprocal_race_creates_one_conversation(self):
        a,b=self.login('maya'),self.login('theo')
        def send(args):
            user,other=args;p=other['app']['me']
            return self.request('POST','/api/likes',dict(target=p['id'],itemType='prompt',itemID=p['prompts'][0]['id']),user['token'])[0]
        with ThreadPoolExecutor(max_workers=2) as pool: self.assertEqual(list(pool.map(send,[(a,b),(b,a)])),[200,200])
        self.assertEqual(len(self.ok('GET','/api/app',token=a['token'])['matches']),1)
        with connect(self.db) as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0],1)

    def test_protected_paths_origin_and_old_snapshot_api(self):
        a=self.login('maya')
        self.assertEqual(self.request('POST','/api/pass',dict(target='x'),a['token'],'https://elsewhere.example')[0],403)
        for path in ['/backend/database.py','/../backend/database.py','/.local/app.sqlite3']:
            self.assertEqual(self.request('GET',path)[0],404)
        self.assertEqual(self.request('PUT','/api/state',dict(state={}),a['token'])[0],404)
        self.assertEqual(self.request('POST','/api/photos',dict(data='not base64'),a['token'])[0],400)

if __name__=='__main__': unittest.main()
