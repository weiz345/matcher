"""Real direct-client browser tests: static host only, hosted Supabase user JWTs."""
import sys,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from test_fixtures import Fixtures
from direct_api import Client,ROOT
sys.path.insert(0,str(ROOT/'scripts'))
from serve_web import StaticHandler
class Quiet(StaticHandler):
 def log_message(self,*_):pass
fixture=Fixtures(3);objects=[]
server=ThreadingHTTPServer(('127.0.0.1',0),Quiet);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=f'http://127.0.0.1:{server.server_port}'
try:
 with sync_playwright()as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
  contexts=[browser.new_context(viewport={'width':1280,'height':1000})for _ in range(3)]
  pages=[c.new_page()for c in contexts];errors=[];api_requests=[]
  for page in pages:
   page.route('https://fonts.googleapis.com/**',lambda route:route.abort())
   page.on('pageerror',lambda error:errors.append(str(error)))
   page.on('request',lambda request:api_requests.append(request.url)if request.url.startswith(base+'/api/')else None)
   page.goto(base,wait_until='domcontentloaded')
  a,b,c=pages
  for page,identity in zip(pages,fixture.identities):
   page.get_by_label('Email',exact=True).fill(identity['email']);page.get_by_label('Password',exact=True).fill(fixture.password)
   page.get_by_role('button',name='Log in',exact=True).click();expect(page.locator('#signed-in')).to_contain_text(identity['name'],timeout=15000)
  a.locator('[data-nav="discover"]').click()
  for _ in range(30):
   if a.locator('[data-like]').first.get_attribute('data-like')==fixture.identities[1]['id']:break
   with a.expect_response(lambda r:r.url.endswith('/rest/v1/rpc/dating_action')and r.request.method=='POST'):
    a.locator('[data-pass]').click()
   expect(a.locator('#database-status')).not_to_have_text('Saving…')
  else:raise AssertionError('Bob not found')
  a.locator(f'[data-like="{fixture.identities[1]["id"]}"][data-kind="prompt"]').click();a.get_by_label('Add a comment').fill('Coffee together?')
  a.get_by_role('button',name='Send like').click();expect(a.locator('#like-dialog')).not_to_be_visible(timeout=15000)
  b.locator('[data-nav="likes"]').click();expect(b.get_by_text('“Coffee together?”',exact=True)).to_be_visible(timeout=15000)
  b.get_by_role('button',name='Like back & match').click();expect(b.locator('.chat-header')).to_contain_text('Alice Test',timeout=15000)
  a.locator('[data-nav="matches"]').click();expect(a.locator('.chat-header')).to_contain_text('Bob Test',timeout=15000)
  a.get_by_role('textbox',name='Your message').fill('Alice direct to Supabase');a.get_by_role('button',name='Send',exact=True).click()
  expect(b.locator('.bubble:not(.mine)')).to_have_text('Alice direct to Supabase',timeout=15000)
  b.get_by_role('textbox',name='Your message').fill('Bob direct to Supabase');b.get_by_role('button',name='Send',exact=True).click()
  expect(a.locator('.bubble:not(.mine)')).to_have_text('Bob direct to Supabase',timeout=15000)
  a.reload(wait_until='domcontentloaded');expect(a.locator('.bubble')).to_have_count(2,timeout=15000)
  # Force session expiry in storage; reloading must refresh the real Supabase token.
  a.evaluate("const k='hinge-supabase-session-v1';const s=JSON.parse(localStorage.getItem(k));s.expires_at=0;localStorage.setItem(k,JSON.stringify(s));")
  a.reload(wait_until='domcontentloaded');expect(a.locator('.bubble')).to_have_count(2,timeout=15000)
  c.locator('[data-nav="profile"]').click();photo=ROOT/'ios/HingeMini/Assets.xcassets/coffee.imageset/coffee.jpg'
  c.locator('#photo-file').set_input_files(photo);expect(c.locator('.photo-grid img')).to_have_count(1,timeout=15000)
  c.wait_for_function("document.querySelector('.photo-grid img')?.naturalWidth > 0",timeout=15000)
  c.get_by_label('Name',exact=True).fill('Carol Persisted');c.get_by_label('Your answer',exact=True).fill('<script>alert(1)</script> Just text.')
  c.get_by_role('button',name='Save profile',exact=True).click();expect(c.locator('#signed-in')).to_contain_text('Carol Persisted',timeout=15000)
  c.reload(wait_until='domcontentloaded');expect(c.get_by_label('Name',exact=True)).to_have_value('Carol Persisted',timeout=15000)
  expect(c.get_by_label('Your answer',exact=True)).to_have_value('<script>alert(1)</script> Just text.')
  a.on('dialog',lambda dialog:dialog.accept());a.get_by_role('button',name='Unmatch',exact=True).click()
  expect(a.get_by_role('heading',name='No matches yet.')).to_be_visible(timeout=15000)
  expect(b.get_by_role('heading',name='No matches yet.')).to_be_visible(timeout=15000)
  b.locator('[data-nav="discover"]').click();old=b.locator('.profile-heading h2').inner_text();b.on('dialog',lambda dialog:dialog.accept())
  b.get_by_role('button',name='Block',exact=True).click();expect(b.locator('.profile-heading h2')).not_to_have_text(old,timeout=15000)
  b.set_viewport_size({'width':390,'height':844});assert b.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
  b.screenshot(path='/tmp/hinge-direct-mobile.png',full_page=True)
  c.get_by_role('button',name='Log out',exact=True).click();expect(c.get_by_role('button',name='Log in',exact=True)).to_be_visible(timeout=15000)
  assert not errors,errors
  assert not api_requests,api_requests
  browser.close()
 print('PASS: direct Supabase login, matching, bidirectional messages, token refresh, private photo upload/load, profile persistence, unmatch/block, logout, mobile layout; ZERO Python API requests.')
finally:
 # Remove test-owned Storage objects through the user API before deleting exact fixture IDs.
 for person in fixture.identities:
  try:
   client=Client().login(person['email'],fixture.password)
   for photo in client.app()['me']['photos']:
    info=client.rpc('dating_photo',{'p_id':photo.split('/')[-1]});client.remove_object(info['path'])
  except Exception:pass
 fixture.cleanup();server.shutdown();server.server_close();thread.join()
