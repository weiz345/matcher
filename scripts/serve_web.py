#!/usr/bin/env python3
"""Static-only web/download host. Application data goes directly to Supabase."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import argparse,mimetypes
ROOT=Path(__file__).resolve().parent.parent
FILES={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css',
       '/supabase-client.js':'supabase-client.js','/supabase-config.js':'supabase-config.js',
       '/hinge-mini-ios.zip':'hinge-mini-ios.zip'}
class StaticHandler(BaseHTTPRequestHandler):
 def do_GET(self):
  name=FILES.get(self.path.split('?')[0]);path=ROOT/name if name else None
  if not path or not path.is_file():self.send_error(404);return
  data=path.read_bytes();self.send_response(200)
  self.send_header('Content-Type',mimetypes.guess_type(name)[0]or'application/octet-stream')
  self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
  self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
  try:self.wfile.write(data)
  except (BrokenPipeError,ConnectionResetError):pass
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--host',default='0.0.0.0');parser.add_argument('--port',type=int,default=8000)
 args=parser.parse_args();print(f'Static web host on http://{args.host}:{args.port}; data goes directly to Supabase',flush=True)
 ThreadingHTTPServer((args.host,args.port),StaticHandler).serve_forever()
