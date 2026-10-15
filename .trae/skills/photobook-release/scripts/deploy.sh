#!/usr/bin/env bash
# Generic GitHub Actions deploy helper.
#
# Pre-flight (fetch + ahead/behind), optional push, optional workflow_dispatch,
# then poll the run to completion. Push and dispatch are OFF unless requested,
# so a bare invocation is a safe dry-run that performs no online mutation.
#
# Usage:
#   deploy.sh [-w WORKFLOW] [-r REF] [--push] [--dispatch] [--go]
#     --push       push the current HEAD to REF after the pre-flight check
#     --dispatch   trigger WORKFLOW on REF (workflow_dispatch) and poll it
#     --go         both --push and --dispatch
#   Without --push/--dispatch/--go: pre-flight + workflow detection only.
#
# WORKFLOW auto-detection: if the repo has exactly one active workflow it is
# used; otherwise pass -w explicitly. Override the dispatchable ref with -r.
set -euo pipefail

REF="main"
WORKFLOW="${DEPLOY_WORKFLOW:-}"
DO_PUSH=0
DO_DISPATCH=0

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    -w|--workflow) WORKFLOW="${2:?-w needs a value}"; shift 2;;
    -r|--ref)      REF="${2:?-r needs a value}"; shift 2;;
    --push)        DO_PUSH=1; shift;;
    --dispatch)    DO_DISPATCH=1; shift;;
    --go)          DO_PUSH=1; DO_DISPATCH=1; shift;;
    -n|--dry-run)  shift;;  # default behaviour; accepted for clarity
    -h|--help)     usage; exit 0;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2;;
  esac
done

command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 2; }
[ -d .git ] || { echo "run this from a git repository root" >&2; exit 2; }

# --- pre-flight: never walk into a non-fast-forward push -------------------
git fetch origin
COUNT="$(git rev-list --left-right --count "HEAD...origin/$REF" 2>/dev/null || echo "? ?")"
AHEAD="$(printf '%s' "$COUNT" | awk '{print $1}')"
BEHIND="$(printf '%s' "$COUNT" | awk '{print $2}')"
HEAD_SHA="$(git rev-parse HEAD)"
echo "ref=$REF head=$HEAD_SHA ahead=$AHEAD behind=$BEHIND"
if [ "$BEHIND" != "0" ]; then
  echo "REFUSING: origin/$REF is ahead. Rebase/merge first." >&2
  exit 1
fi

# --- auto-detect the workflow when there is exactly one active -------------
if [ -z "$WORKFLOW" ]; then
  NAMES="$(gh workflow list --json name,state --jq '.[] | select(.state=="active") | .name')"
  N="$(printf '%s\n' "$NAMES" | grep -c . || true)"
  if [ "$N" = "1" ]; then
    WORKFLOW="$(printf '%s' "$NAMES" | head -n1)"
    echo "workflow(auto)=$WORKFLOW"
  else
    echo "REFUSING: $N active workflows; pass -w \"<name>\"" >&2
    printf '%s\n' "$NAMES" >&2
    exit 2
  fi
else
  echo "workflow=$WORKFLOW"
fi

if [ "$DO_PUSH" -eq 0 ] && [ "$DO_DISPATCH" -eq 0 ]; then
  echo "dry-run only (nothing pushed/dispatched). Re-run with --push/--dispatch/--go."
  exit 0
fi

# --- push -------------------------------------------------------------------
if [ "$DO_PUSH" -eq 1 ]; then
  if [ "$AHEAD" = "0" ]; then
    echo "nothing to push (local not ahead)"
  else
    git push origin "HEAD:$REF"
  fi
fi

# --- dispatch and verify it runs the pushed commit --------------------------
if [ "$DO_DISPATCH" -eq 1 ]; then
  gh workflow run "$WORKFLOW" --ref "$REF"
  sleep 12
  read -r RUN_ID RUN_SHA RUN_EVENT < <(
    gh run list --workflow="$WORKFLOW" --branch "$REF" --limit 1 \
      --json databaseId,headSha,event \
      --jq '.[0] | [.databaseId,.headSha,.event] | map(tostring) | join(" ")'
  )
  echo "run=$RUN_ID event=$RUN_EVENT sha=$RUN_SHA"
  [ "$RUN_EVENT" = "workflow_dispatch" ] || echo "WARN: event is $RUN_EVENT" >&2
  [ "$RUN_SHA" = "$HEAD_SHA" ] || echo "WARN: run sha $RUN_SHA != head $HEAD_SHA" >&2

  # Poll up to ~25 min (100 x 15s); long retries (e.g. API quota windows) are normal.
  I=0
  while [ "$I" -lt 100 ]; do
    STATE="$(gh run view "$RUN_ID" --json status,conclusion --jq '"\(.status) \(.conclusion)"')"
    echo "[$((I * 15))s] $STATE"
    case "$STATE" in completed*) break;; esac
    sleep 15
    I=$((I + 1))
  done
  REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
  echo "https://github.com/$REPO/actions/runs/$RUN_ID"
  case "$STATE" in
    "completed success") exit 0;;
    *) echo "run did not succeed: $STATE" >&2
       gh run view "$RUN_ID" --log-failed >&2 || true
       exit 1;;
  esac
fi
