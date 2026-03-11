#!/bin/bash

if [ ! -d "./site-mirror" ] || [ -z "$(ls -A ./site-mirror)" ]; then
  bash scripts/create-mirror-site.sh
fi

python3 -c "
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
os.chdir('site-mirror')
class H(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
HTTPServer(('', 8080), H).serve_forever()
"
