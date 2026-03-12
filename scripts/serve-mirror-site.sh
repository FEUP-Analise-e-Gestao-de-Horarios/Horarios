#!/bin/bash

if [ ! -d "./site-mirror" ] || [ -z "$(ls -A ./site-mirror)" ]; then
  bash scripts/create-mirror-site.sh
fi

cd ./site-mirror
python -m http.server 8080
