#!/usr/bin/env python3
"""Local account-based dating MVP API and web server (Python standard library)."""
import argparse
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from storage import is_postgres
from database import (APIError, ROOT, connect, initialize, create_account, issue_session,
                      user_for_token, person, visible, require_person, app_state,
                      conversation, messages, like, update_profile, upload_photo, text, password_hash)

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def send(self, status, data, mime='application/json', cookie=None):
        if mime=='application/json': data=json.dumps(data,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','same-origin')
        if cookie is not None:
            secure='; Secure' if self.server.secure_cookies else ''
            self.send_header('Set-Cookie',f'hinge_auth={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={2592000 if cookie else 0}{secure}')
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError): pass

    def token(self):
        auth=self.headers.get('Authorization','')
        if auth.startswith('Bearer '): return auth[7:]
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: return ''
        return cookie['hinge_auth'].value if 'hinge_auth' in cookie else ''

    def body(self):
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise APIError(400,'Invalid request size')
        if not 0<length<=5*1024*1024: raise APIError(413,'Request must be at most 5 MB')
        if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise APIError(415,'Expected application/json')
        try: body=json.loads(self.rfile.read(length))
        except (ValueError,UnicodeError): raise APIError(400,'Invalid JSON')
        if not isinstance(body,dict): raise APIError(400,'Expected JSON object')
        return body

    def route(self, method):
        url=urlsplit(self.path); path=url.path; parts=path.strip('/').split('/')
        if method!='GET':
            origin=self.headers.get('Origin')
            if origin and urlsplit(origin).netloc!=self.headers.get('Host'): raise APIError(403,'Origin not allowed')
        if path=='/api/health' and method=='GET': return self.send(200,dict(ok=True,storage='postgresql' if is_postgres(self.server.db_path) else 'sqlite',mode='accounts'))
        if not path.startswith('/api/'):
            if method!='GET': raise APIError(405,'Method not allowed')
            static={'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),
                    '/app.js':('app.js','text/javascript; charset=utf-8'),
                    '/supabase-client.js':('supabase-client.js','text/javascript; charset=utf-8'),
                    '/supabase-config.js':('supabase-config.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8'),
                    '/hinge-mini-ios.zip':('hinge-mini-ios.zip','application/zip')}
            if path not in static: raise APIError(404,'Not found')
            file,mime=static[path]
            return self.send(200,(ROOT/file).read_bytes(),mime)
        body=self.body() if method in ('POST','PUT') else {}
        with connect(self.server.db_path) as db:
            if method!='GET': db.execute('BEGIN IMMEDIATE')
            if path in ('/api/signup','/api/login') and method=='POST':
                email=text(body,'email',254).lower()
                self.throttle(email)
                if path=='/api/signup': me=create_account(db,body)
                else:
                    password=body.get('password','')
                    if not isinstance(password,str) or len(password)>128: raise APIError(401,'Invalid email or password')
                    row=db.execute('SELECT * FROM accounts WHERE email=?',(email,)).fetchone()
                    digest=password_hash(password,row['salt'] if row else '00'*16)
                    if not row or not secrets.compare_digest(digest,row['password_hash']): raise APIError(401,'Invalid email or password')
                    me=row['id']
                token=issue_session(db,me); data=dict(token=token,app=app_state(db,me))
                db.commit()
                return self.send(201 if path=='/api/signup' else 200,data,cookie=token)
            token=self.token()
            me=user_for_token(db,token)
            if method=='GET':
                if path=='/api/app': return self.send(200,app_state(db,me))
                if len(parts)==3 and parts[:2]==['api','photos']:
                    row=db.execute('SELECT * FROM photos WHERE id=?',(parts[2],)).fetchone()
                    if not row or (row['user_id']!=me and not visible(db,me,row['user_id'])): raise APIError(404,'Photo unavailable')
                    return self.send(200,row['data'],row['mime'])
                if len(parts)==4 and parts[:2]==['api','conversations'] and parts[3]=='messages':
                    try: before=int(parse_qs(url.query).get('before',['9223372036854775807'])[0])
                    except ValueError: raise APIError(400,'Invalid message cursor')
                    if not 0<before<=9223372036854775807: raise APIError(400,'Invalid message cursor')
                    return self.send(200,dict(messages=messages(db,me,parts[2],before)))
                raise APIError(404,'Not found')
            result={}
            if path=='/api/logout' and method=='POST':
                db.execute('DELETE FROM auth_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),));db.commit()
                return self.send(200,dict(ok=True),cookie='')
            elif path=='/api/profile' and method=='PUT': update_profile(db,me,body)
            elif path=='/api/photos' and method=='POST': result['photoID']=upload_photo(db,me,body)
            elif len(parts)==3 and parts[:2]==['api','photos'] and method=='DELETE':
                if not db.execute('DELETE FROM photos WHERE id=? AND user_id=?',(parts[2],me)).rowcount: raise APIError(404,'Photo unavailable')
            elif path=='/api/likes' and method=='POST':
                result['matchID']=like(db,me,text(body,'target',40),text(body,'itemType',10),text(body,'itemID',100),text(body,'comment',300,False))
            elif len(parts)==4 and parts[:2]==['api','likes'] and parts[3]=='accept' and method=='POST':
                target=parts[2];require_person(db,me,target)
                if not db.execute('SELECT 1 FROM user_likes WHERE sender=? AND recipient=?',(target,me)).fetchone(): raise APIError(404,'Like unavailable')
                p=person(db,target)
                if p['photos']: kind,item='photo',p['photos'][0].split('/')[-1]
                else: kind,item='prompt',p['prompts'][0]['id']
                result['matchID']=like(db,me,target,kind,item,'')
            elif path=='/api/pass' and method=='POST':
                target=text(body,'target',40);require_person(db,me,target)
                db.execute('INSERT OR IGNORE INTO passes VALUES (?,?)',(me,target))
            elif path=='/api/passes' and method=='DELETE': db.execute('DELETE FROM passes WHERE user_id=?',(me,))
            elif len(parts)==4 and parts[:2]==['api','conversations'] and parts[3]=='messages' and method=='POST':
                cid=parts[2];conversation(db,me,cid)
                message=text(body,'text',1000);client_id=text(body,'clientID',100)
                db.execute('INSERT OR IGNORE INTO chat_messages(conversation_id,sender,text,created_at,client_id) VALUES (?,?,?,?,?)',(cid,me,message,int(time.time()),client_id))
            elif len(parts)==3 and parts[:2]==['api','conversations'] and method=='DELETE':
                conversation(db,me,parts[2]);db.execute('UPDATE conversations SET active=0 WHERE id=?',(parts[2],))
            elif path=='/api/blocks' and method=='POST':
                target=text(body,'target',40);require_person(db,me,target)
                db.execute('INSERT OR IGNORE INTO user_blocks VALUES (?,?)',(me,target))
                a,b=sorted([me,target]);db.execute('UPDATE conversations SET active=0 WHERE a=? AND b=?',(a,b))
                db.execute('DELETE FROM user_likes WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)',(me,target,target,me))
            else: raise APIError(404,'Not found')
            result['app']=app_state(db,me);db.commit()
            return self.send(200,result)

    def throttle(self,email):
        key=(self.client_address[0],email)
        now=time.monotonic()
        with self.server.rate_lock:
            attempts=self.server.attempts[key]
            while attempts and attempts[0]<now-60: attempts.popleft()
            if len(attempts)>=20: raise APIError(429,'Too many attempts. Try again in a minute.')
            attempts.append(now)

    def handle_request(self,method):
        try: self.route(method)
        except APIError as e: self.send(e.status,dict(error=e.message))
        except (ValueError,TypeError,KeyError,OverflowError): self.send(400,dict(error='Invalid request'))
        except sqlite3.Error:
            self.log_error('Database operation failed')
            self.send(503,dict(error='Database unavailable. Try again.'))

    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_PUT(self): self.handle_request('PUT')
    def do_DELETE(self): self.handle_request('DELETE')

def make_server(host,port,db_path,secure_cookies=False,seed=None):
    initialize(db_path,seed=seed)
    server=ThreadingHTTPServer((host,port),Handler)
    server.db_path=str(db_path);server.secure_cookies=secure_cookies
    server.attempts=defaultdict(deque);server.rate_lock=threading.Lock()
    return server

if __name__=='__main__':
    from config import load_env
    load_env()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='0.0.0.0');parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--db',default=str(Path.home()/'.local/share/hinge-mini/app.sqlite3'))
    parser.add_argument('--seed-test-accounts',action='store_true',default=None,help='Seed known test accounts (off by default on PostgreSQL)')
    parser.add_argument('--secure-cookies',action='store_true',help='Use behind HTTPS')
    args=parser.parse_args()
    target=os.environ.get('HINGE_DATABASE_URL') or args.db
    server=make_server(args.host,args.port,target,args.secure_cookies,seed=args.seed_test_accounts)
    print(f'Account MVP on http://{args.host}:{args.port}',flush=True)
    server.serve_forever()
