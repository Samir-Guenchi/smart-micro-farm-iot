#!/bin/sh
# Assembles the public site in _site/: this folder plus the shared data/ folder
# (the crop calendar reads data/crop-calendar.json). Used by the Pages workflow
# and for local preview:  ./site/build.sh && python3 -m http.server -d _site
set -e
cd "$(dirname "$0")/.."
rm -rf _site
mkdir -p _site
cp -R site/. _site/
rm -f _site/build.sh _site/README.md
if [ -d data ]; then cp -R data _site/data; fi
echo "built _site/"
