#!/bin/bash

if [ -d "./site-mirror" ]; then
  rm -rf ./site-mirror
fi

wget --mirror --convert-links --adjust-extension --page-requisites --no-parent \
  --no-host-directories --cut-dirs=3 \
  -e robots=off \
  -P ./site-mirror https://fe.up.pt/horarios/25_26_2s/final/
