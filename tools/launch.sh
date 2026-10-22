#!/bin/zsh
# Makes the launch page the front page once the app is on the App Store:
# launch.html replaces index.html, loses its noindex, gains the front page's
# canonical, and /launch stops existing. The sign-up form goes with the old
# index.html. Leaves the result uncommitted; check it, then commit and push.
#
#   tools/launch.sh
set -euo pipefail
cd "${0:A:h}/.."
[[ -f launch.html ]] || { print -u2 "No launch.html: already launched?"; exit 1; }
[[ -z $(git status --porcelain index.html launch.html) ]] ||
  { print -u2 "index.html or launch.html has uncommitted changes"; exit 1; }

git mv -f launch.html index.html
perl -0pi -e 's|<meta name="robots" content="noindex, nofollow">\n||; s|^(?=<meta property="og:title")|<link rel="canonical" href="https://timelasso.app/">\n|m' index.html

fail() { print -u2 "launch.sh: $1"; exit 1; }
grep -q noindex index.html && fail "noindex still there"
(( $(grep -c '<link rel="canonical" href="https://timelasso.app/">' index.html) == 1 )) ||
  fail "expected one front-page canonical"
grep -q buttondown index.html && fail "sign-up form still there"
grep -q 'apps.apple.com/app/id' index.html || fail "no App Store link"
git status --short
print "Front page swapped. Commit and push to publish."
