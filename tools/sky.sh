#!/bin/zsh
# Turns a Timelasso clip into the page's background: a portrait cut for phones
# and a landscape cut for wide screens, each looped with a one-second
# crossfade from its last second into its first, plus each loop's first frame
# as the still shown while it loads and under reduced motion.
#
#   tools/sky.sh clip.MOV [x]
#
# x places the portrait slice across the frame, 0 = left edge, 1 = right,
# default 0.5; use it when the subject of a new take isn't central. Writes
# sky-{tall,wide}.{mp4,jpg} beside index.html; commit and push to publish.
set -euo pipefail
src=$1
x=${2:-0.5}
cd "${0:A:h}/.."

dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$src")
end=$(( dur - 1 ))

cut() { # name, geometry
  ffmpeg -v error -y -hwaccel videotoolbox -i "$src" -an -filter_complex "\
[0:v]fps=30,$2,scale=out_range=tv,format=yuv420p,setsar=1,split=3[a][b][c];\
[a]trim=1:$end,setpts=PTS-STARTPTS,fps=30[mid];\
[b]trim=$end:$dur,setpts=PTS-STARTPTS,fps=30[tail];\
[c]trim=0:1,setpts=PTS-STARTPTS,fps=30[head];\
[tail][head]xfade=transition=fade:duration=1:offset=0[join];\
[mid][join]concat=n=2:v=1[out]" \
    -map "[out]" -c:v libx264 -preset slow -crf 26 -profile:v high -movflags +faststart "$1.mp4"
  ffmpeg -v error -y -i "$1.mp4" -frames:v 1 -q:v 4 -update 1 "$1.jpg"
}

# The portrait slice is 9:16 of the full height, as sharp as the source allows.
cut sky-wide "scale=1280:720" &
cut sky-tall "crop=ih*9/16:ih:(iw-ih*9/16)*$x:0,scale=720:1280" &
wait
ls -la sky-*
