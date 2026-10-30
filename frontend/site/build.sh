#!/bin/sh
# Assembles the public site in frontend/site/_site/: this folder plus the shared data/
# folder (the crop calendar reads data/crop-calendar.json). Used by the Pages
# workflow and for local preview:
#   ./frontend/site/build.sh && python3 -m http.server -d frontend/site/_site
set -e
cd "$(dirname "$0")"
rm -rf _site
mkdir _site
tar --exclude=./_site --exclude=./build.sh --exclude=./README.md --exclude=./.gitignore -cf - . | tar -C _site -xf -
if [ -d ../../data ]; then cp -R ../../data _site/data; fi
echo "built frontend/site/_site/"
