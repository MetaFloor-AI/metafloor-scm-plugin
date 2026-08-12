#!/usr/bin/env bash
# render <diagram-basename>  -> assets/img/<basename>.png  (2x, tight-cropped, white margin)
set -e
name="$1"; src="$PWD/assets/diagrams/${name}.html"; out="$PWD/assets/img/${name}.png"
google-chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --screenshot="$out" --window-size=1120,2200 "file://${src}" >/dev/null 2>&1
convert "$out" -trim +repage -bordercolor white -border 40 "$out"
echo "$(basename "$out"): $(identify -format '%wx%h' "$out")"
