#!/usr/bin/env python3
"""Browser smoke test; requires playwright and installed Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
 with sync_playwright()as p:
  browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.route('**/api/status',lambda route:route.fulfill(json={'count':1000,'ready':False,'progress':{'done':250,'total':1000,'elapsed_seconds':25,'images_per_second':10,'eta_seconds':75,'phase':'embedding'}}))
  page.goto('http://127.0.0.1:8001')
  page.wait_for_function("document.querySelector('#embedding-bar').value===25")
  assert '1m 15s remaining' in page.locator('#embedding-details').inner_text()
  assert '10.0 images/s' in page.locator('#embedding-details').inner_text()
  page.unroute('**/api/status');page.reload()
  page.wait_for_function("document.querySelector('#embedding-bar').value===100")
  assert page.locator('#embedding-title').inner_text()=='Embedding complete'
  page.get_by_role('button',name='Browse synthetic faces').click()
  page.locator('#gallery-grid .tile').first.wait_for()
  assert page.locator('#gallery-grid .tile').count()==24
  page.wait_for_function("document.querySelector('#gallery-grid img').complete && document.querySelector('#gallery-grid img').naturalWidth>0")
  page.locator('#gallery-grid button').first.click()
  page.locator('#k').fill('7');page.locator('#k').dispatch_event('input')
  page.locator('#search').click();page.wait_for_function("document.querySelectorAll('#results-grid .tile').length===7")
  page.select_option('#transform','flip');page.locator('#search').click()
  page.wait_for_function("document.querySelector('#query-used').textContent.includes('flip')")
  page.get_by_role('tab',name='Robustness checks').click();page.locator('.eval-card').first.wait_for()
  assert page.locator('.eval-card').count()==3
  file=next((Path(__file__).parent/'data/images').glob('*.jpg'))
  page.locator('#upload').set_input_files(str(file))
  page.wait_for_function("document.querySelector('#query-preview').src.startsWith('data:')")
  with page.expect_response('**/api/search')as response:page.locator('#search').click()
  assert response.value.status==200
  page.wait_for_function("!document.querySelector('#search').disabled")
  page.screenshot(path='/tmp/image-lab-desktop.png',full_page=True)
  page.set_viewport_size({'width':390,'height':844})
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
  page.screenshot(path='/tmp/image-lab-mobile.png',full_page=True)
  assert not errors,errors
  browser.close();print('PASS: gallery, image loading, 7 neighbors, flip query, evaluation, file upload, mobile layout; no browser errors.')
if __name__=='__main__':main()
