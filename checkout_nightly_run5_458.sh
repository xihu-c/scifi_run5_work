#!/bin/bash
# Check out nightly build lhcb-run5/458 in each project, then rebuild Moore.
# Run from the stack root. Commit or stash local changes first:
# each project ends up on a detached HEAD.
# The tag name follows the lhcb-master/1767 example in utils/README.md; it is untested.
set -e
cd "$(dirname "$0")/.."

PROJECTS="Gaudi Detector LHCb Lbcom Rec Moore Allen"
TAG="lhcb-run5/458"

for p in $PROJECTS; do
  echo "=== $p"
  (cd "$p" && git fetch "ssh://git@gitlab.cern.ch:7999/lhcb-nightlies/$p.git" "$TAG" && git checkout FETCH_HEAD)
done

for p in $PROJECTS; do
  echo "$p: $(git -C "$p" rev-parse --short HEAD)"
done

# make purge
# make Moore
