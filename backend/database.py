"""Account-owned relational storage. Legacy demo tables are intentionally untouched."""
import base64
import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from storage import connect_database, is_postgres

ROOT = Path(__file__).resolve().parent.parent
SEED_PASSWORD = 'HingeTest2026!'

class APIError(Exception):
    def __init__(self, status, message): self.status, self.message = status, message

def connect(path):
    return connect_database(path)

def uid(): return uuid.uuid4().hex

def text(body, key, limit, required=True):
    value = body.get(key, '')
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise APIError(400, 'Invalid ' + key)
    return value.strip()

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()

def create_account(db, body):
    email = text(body, 'email', 254).lower()
    if '@' not in email or '.' not in email.split('@')[-1]: raise APIError(400, 'Enter a valid email')
    password = body.get('password')
    if not isinstance(password, str) or not 10 <= len(password) <= 128: raise APIError(400, 'Password must be 10–128 characters')
    name = text(body, 'name', 40)
    age = body.get('age')
    if type(age) is not int or not 18 <= age <= 120: raise APIError(400, 'Age must be 18–120')
    account, salt = uid(), secrets.token_hex(16)
    try:
        db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (account, email, salt, password_hash(password, salt), name, age, 'Brooklyn', '', '', int(time.time())))
    except sqlite3.IntegrityError: raise APIError(409, 'An account with that email already exists')
    db.execute('INSERT INTO prompts VALUES (?,?,?,?,?)', (uid(), account, 'My simple pleasures', 'Good coffee and great conversation.', 0))
    return account

def initialize(path, seed=None):
    if not is_postgres(path): Path(path).parent.mkdir(parents=True, exist_ok=True)
    if seed is None: seed = not is_postgres(path)
    with connect(path) as db:
        db.execute('PRAGMA journal_mode=WAL')
        if is_postgres(path):
            db.execute('SELECT pg_advisory_xact_lock(723194042)')
            db.execute('CREATE SCHEMA IF NOT EXISTS hinge')
            db.execute('REVOKE ALL ON SCHEMA hinge FROM PUBLIC')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS accounts (
          id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,salt TEXT NOT NULL,password_hash TEXT NOT NULL,
          name TEXT NOT NULL,age INTEGER NOT NULL CHECK(age>=18),location TEXT NOT NULL,
          job TEXT NOT NULL,height TEXT NOT NULL,created_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS auth_sessions (
          token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES accounts(id),expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS prompts (
          id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES accounts(id),title TEXT NOT NULL,answer TEXT NOT NULL,position INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS photos (
          id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES accounts(id),mime TEXT NOT NULL,data BLOB NOT NULL,position INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS user_likes (
          sender TEXT NOT NULL REFERENCES accounts(id),recipient TEXT NOT NULL REFERENCES accounts(id),
          item_type TEXT NOT NULL,item_id TEXT NOT NULL,comment TEXT NOT NULL,created_at INTEGER NOT NULL,
          PRIMARY KEY(sender,recipient),CHECK(sender<>recipient));
        CREATE TABLE IF NOT EXISTS conversations (
          id TEXT PRIMARY KEY,a TEXT NOT NULL REFERENCES accounts(id),b TEXT NOT NULL REFERENCES accounts(id),
          active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,UNIQUE(a,b),CHECK(a<b));
        CREATE TABLE IF NOT EXISTS chat_messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL REFERENCES conversations(id),
          sender TEXT NOT NULL REFERENCES accounts(id),text TEXT NOT NULL,created_at INTEGER NOT NULL,
          client_id TEXT NOT NULL,UNIQUE(conversation_id,sender,client_id));
        CREATE TABLE IF NOT EXISTS user_blocks (
          blocker TEXT NOT NULL REFERENCES accounts(id),blocked TEXT NOT NULL REFERENCES accounts(id),
          PRIMARY KEY(blocker,blocked),CHECK(blocker<>blocked));
        CREATE TABLE IF NOT EXISTS passes (
          user_id TEXT NOT NULL REFERENCES accounts(id),target TEXT NOT NULL REFERENCES accounts(id),PRIMARY KEY(user_id,target));
        CREATE INDEX IF NOT EXISTS likes_recipient ON user_likes(recipient);
        CREATE INDEX IF NOT EXISTS messages_conversation ON chat_messages(conversation_id,id);
        ''')
        if not seed: return
        seeds = [('maya','Maya',28,'Product designer'),('theo','Theo',31,'Pastry chef'),('priya','Priya',29,'Urban planner'),('jonah','Jonah',33,'Nurse'),('lena','Lena',30,'Architect'),('marcus','Marcus',32,'Music teacher')]
        for key, name, age, job in seeds:
            if db.execute('SELECT 1 FROM accounts WHERE email=?', (key+'@hinge.test',)).fetchone(): continue
            account = create_account(db, dict(email=key+'@hinge.test',password=SEED_PASSWORD,name=name,age=age))
            db.execute('UPDATE accounts SET job=? WHERE id=?',(job,account))
            file = ROOT/f'ios/HingeMini/Assets.xcassets/{key}.imageset/{key}.jpg'
            if file.exists(): db.execute('INSERT INTO photos VALUES (?,?,?,?,?)',(uid(),account,'image/jpeg',file.read_bytes(),0))

def issue_session(db, user):
    token = secrets.token_urlsafe(32)
    db.execute('INSERT INTO auth_sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user,int(time.time())+30*86400))
    return token

def user_for_token(db, token):
    row = db.execute('SELECT user_id FROM auth_sessions WHERE token_hash=? AND expires_at>?',
                     (hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
    if not row: raise APIError(401,'Please log in')
    return row['user_id']

def visible(db, me, other):
    return me != other and not db.execute('SELECT 1 FROM user_blocks WHERE (blocker=? AND blocked=?) OR (blocker=? AND blocked=?)',(me,other,other,me)).fetchone()

def require_person(db, me, other):
    if not visible(db,me,other) or not db.execute('SELECT 1 FROM accounts WHERE id=?',(other,)).fetchone(): raise APIError(404,'Profile unavailable')

def person(db, account):
    row = db.execute('SELECT id,name,age,location,job,height FROM accounts WHERE id=?',(account,)).fetchone()
    result = dict(row)
    result['photos'] = ['/api/photos/'+r['id'] for r in db.execute('SELECT id FROM photos WHERE user_id=? ORDER BY position,id LIMIT 6',(account,))]
    result['prompts'] = [dict(r) for r in db.execute('SELECT id,title,answer FROM prompts WHERE user_id=? ORDER BY position,id LIMIT 3',(account,))]
    return result

def conversation(db, me, cid):
    row = db.execute('SELECT * FROM conversations WHERE id=? AND active=1 AND (a=? OR b=?)',(cid,me,me)).fetchone()
    if not row: raise APIError(404,'Conversation unavailable')
    other = row['b'] if row['a']==me else row['a']
    if not visible(db,me,other): raise APIError(404,'Conversation unavailable')
    return other

def messages(db, me, cid, before=9223372036854775807):
    conversation(db,me,cid)
    rows = db.execute('SELECT * FROM chat_messages WHERE conversation_id=? AND id<? ORDER BY id DESC LIMIT 100',(cid,before)).fetchall()
    return [dict(id=str(r['id']),text=r['text'],mine=r['sender']==me,senderID=r['sender'],createdAt=r['created_at']) for r in reversed(rows)]

def app_state(db, me):
    own = person(db,me)
    candidates = db.execute('''SELECT id FROM accounts x WHERE id<>?
        AND NOT EXISTS(SELECT 1 FROM user_blocks WHERE (blocker=? AND blocked=x.id) OR (blocked=? AND blocker=x.id))
        AND NOT EXISTS(SELECT 1 FROM passes WHERE user_id=? AND target=x.id)
        AND NOT EXISTS(SELECT 1 FROM user_likes WHERE sender=? AND recipient=x.id)
        AND NOT EXISTS(SELECT 1 FROM conversations WHERE (a=? AND b=x.id) OR (b=? AND a=x.id))
        ORDER BY created_at,id LIMIT 100''',(me,me,me,me,me,me,me)).fetchall()
    likes=[]
    for row in db.execute('''SELECT * FROM user_likes l WHERE recipient=?
         AND NOT EXISTS(SELECT 1 FROM passes WHERE user_id=? AND target=l.sender)
         AND NOT EXISTS(SELECT 1 FROM conversations WHERE (a=? AND b=l.sender) OR (b=? AND a=l.sender))
         ORDER BY created_at DESC LIMIT 100''',(me,me,me,me)):
        if visible(db,me,row['sender']):
            likes.append(dict(id=row['sender'],person=person(db,row['sender']),comment=row['comment'],itemType=row['item_type'],itemID=row['item_id']))
    matches=[]
    for row in db.execute('SELECT * FROM conversations WHERE active=1 AND (a=? OR b=?) ORDER BY created_at DESC LIMIT 100',(me,me)):
        other = row['b'] if row['a']==me else row['a']
        if visible(db,me,other): matches.append(dict(id=row['id'],person=person(db,other),messages=messages(db,me,row['id'])))
    return dict(me=own,discover=[person(db,r['id']) for r in candidates],likes=likes,matches=matches)

def like(db, me, target, item_type, item_id, comment):
    require_person(db,me,target)
    a,b=sorted([me,target])
    old=db.execute('SELECT * FROM conversations WHERE a=? AND b=?',(a,b)).fetchone()
    if old:
        if not old['active']: raise APIError(409,'This connection has ended')
        return old['id']
    table={'photo':'photos','prompt':'prompts'}.get(item_type)
    if not table or not db.execute(f'SELECT 1 FROM {table} WHERE id=? AND user_id=?',(item_id,target)).fetchone(): raise APIError(400,'Like must reference this person’s photo or prompt')
    db.execute('INSERT INTO user_likes VALUES (?,?,?,?,?,?) ON CONFLICT(sender,recipient) DO NOTHING',(me,target,item_type,item_id,comment,int(time.time())))
    db.execute('DELETE FROM passes WHERE user_id=? AND target=?',(me,target))
    if db.execute('SELECT 1 FROM user_likes WHERE sender=? AND recipient=?',(target,me)).fetchone():
        cid=uid()
        db.execute('INSERT INTO conversations(id,a,b,created_at) VALUES (?,?,?,?)',(cid,a,b,int(time.time())))
        return cid
    return None

def update_profile(db, me, body):
    name, location = text(body,'name',40),text(body,'location',80)
    age=body.get('age')
    if type(age) is not int or not 18<=age<=120: raise APIError(400,'Age must be 18–120')
    prompts=body.get('prompts')
    if not isinstance(prompts,list) or not 1<=len(prompts)<=3: raise APIError(400,'Provide 1–3 prompts')
    db.execute('UPDATE accounts SET name=?,age=?,location=?,job=?,height=? WHERE id=?',(name,age,location,text(body,'job',80,False),text(body,'height',30,False),me))
    owned={r['id'] for r in db.execute('SELECT id FROM prompts WHERE user_id=?',(me,))}
    kept=set()
    for i,p in enumerate(prompts):
        if not isinstance(p,dict): raise APIError(400,'Invalid prompt')
        title,answer=text(p,'title',100),text(p,'answer',300)
        pid=p.get('id') if p.get('id') in owned else uid()
        if pid in kept: raise APIError(400,'Duplicate prompt')
        kept.add(pid)
        db.execute('INSERT INTO prompts VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,answer=excluded.answer,position=excluded.position',(pid,me,title,answer,i))
    for pid in owned-kept: db.execute('DELETE FROM prompts WHERE id=? AND user_id=?',(pid,me))

def upload_photo(db, me, body):
    encoded=text(body,'data',5*1024*1024)
    try: data=base64.b64decode(encoded,validate=True)
    except Exception: raise APIError(400,'Invalid base64 image')
    if not 8<=len(data)<=3*1024*1024: raise APIError(400,'Photo must be at most 3 MB')
    mime='image/jpeg' if data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9') else 'image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else None
    if not mime: raise APIError(400,'Upload JPEG or PNG')
    count=db.execute('SELECT COUNT(*) FROM photos WHERE user_id=?',(me,)).fetchone()[0]
    if count>=6: raise APIError(400,'Maximum 6 photos; remove one first')
    pid=uid()
    db.execute('INSERT INTO photos VALUES (?,?,?,?,?)',(pid,me,mime,data,count))
    return pid
