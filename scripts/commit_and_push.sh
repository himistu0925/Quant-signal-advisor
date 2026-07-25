#!/usr/bin/env bash
# Commits the given paths and pushes, retrying on a rejected push instead of
# failing outright. All workflows that write repo state share one
# concurrency group (see schedule.yml), but that only serializes when two
# runs happen to overlap by more than a few seconds -- a push can still land
# on a stale base and get rejected. On rejection this rebases onto the new
# tip and retries. docs/index.html is the one file multiple workflows
# (schedule.yml, add_ticker.yml, remove_ticker.yml) regenerate independently,
# so a real rebase conflict there is expected occasionally; set
# REGENERATE_DASHBOARD=1 (workflows that call generate_dashboard.py) to
# resolve it by regenerating fresh from the now-rebased state rather than
# hand-merging generated HTML. Workflows whose paths no other workflow
# touches (universe_scan.yml, calibrate.yml) should leave it unset -- a
# conflict there would be unexpected, so fail loudly instead of guessing.
#
# Usage: commit_and_push.sh "<commit message>" <path> [<path> ...]
set -euo pipefail

# No interactive terminal on a GitHub Actions runner -- if git ever wants to
# open an editor (e.g. during rebase --continue) or prompt for credentials,
# make sure that can't hang the job.
export GIT_EDITOR=true
export GIT_TERMINAL_PROMPT=0

MSG="$1"
shift
PATHS=("$@")

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add "${PATHS[@]}"
if git diff --staged --quiet; then
  echo "Nothing to commit."
  exit 0
fi
git commit -m "$MSG"

for attempt in 1 2 3 4 5; do
  if git push; then
    echo "Pushed on attempt $attempt."
    exit 0
  fi

  echo "Push rejected on attempt $attempt -- another workflow updated the repo first. Rebasing and retrying."
  git fetch origin master
  if ! git rebase origin/master; then
    if [ "${REGENERATE_DASHBOARD:-0}" = "1" ]; then
      echo "Rebase conflict -- regenerating the dashboard instead of merging generated HTML by hand."
      python scripts/generate_dashboard.py
      git add docs/
      git rebase --continue
    else
      echo "::error::Rebase conflict with no regeneration fallback configured for this workflow."
      git rebase --abort
      exit 1
    fi
  fi
  sleep $((attempt * 5))
done

echo "::error::Failed to push after 5 attempts"
exit 1
