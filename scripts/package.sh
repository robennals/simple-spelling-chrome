#!/usr/bin/env bash
# Build the Chrome Web Store upload: dist/simple-spelling-<version>.zip,
# containing exactly the files the extension needs.
set -euo pipefail
cd "$(dirname "$0")/.."

version=$(python3 -c 'import json; print(json.load(open("extension/manifest.json"))["version"])')
out="dist/simple-spelling-${version}.zip"
files=(
  manifest.json
  content.js
  respell.js
  popup.html
  popup.js
  respellings.json
  phonetic.json
  THIRD_PARTY_NOTICES.txt
  icons/icon16.png
  icons/icon32.png
  icons/icon48.png
  icons/icon128.png
)

for f in "${files[@]}"; do
  [[ -f "extension/$f" ]] || { echo "missing extension/$f" >&2; exit 1; }
done

mkdir -p dist
rm -f "$out"
(cd extension && zip -q -X "../$out" "${files[@]}")
echo "$out"
unzip -l "$out"
