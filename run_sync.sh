#!/bin/zsh
#
# launchd entry point for the scheduled Tastytrade sync.
#
# Wraps run_today_prod.py so that a crash which prevents the job from writing
# its own Sync Log heartbeat still gets recorded in the sheet. Without this,
# an import-time failure produces a completely silent outage — see
# report_crash.py for the history.
#
# Two guards before the sync runs:
#   1. Refuse to run from an iCloud-synced path. The 2026-07-16 and 2026-07-23
#      outages were both caused by iCloud evicting this repo's source files to
#      dataless stubs, which a background launchd job cannot materialize
#      (reads fail with EDEADLK). If the repo ever drifts back under
#      ~/Documents or ~/Desktop, fail loudly here instead of mysteriously.
#   2. Verify the source files are actually readable, so an unreadable-file
#      failure is reported as such rather than as a Python traceback.

set -u

REPO_DIR="/Users/Kevin/dev/tastytrade-logger"
PYTHON="/Users/Kevin/miniconda3/bin/python3"
LOG_DIR="/Users/Kevin/Library/Logs/tastytrade-logger"
CRASH_LOG="${LOG_DIR}/last-crash.log"
# run_today_prod.py touches this once it has written its own Sync Log row.
# Its absence after a failed run is what tells us the job died before it could
# report itself. Exit code cannot tell us: an import crash and a handled error
# both exit 1.
HEARTBEAT_MARKER="${LOG_DIR}/.self-reported"

# Hard wall-clock cap on the sync (seconds). If it ever hangs — e.g. a network
# read with no timeout — kill it so launchd is free to start the next scheduled
# run. On 2026-07-23 a single run hung mid-fetch and never exited; because
# launchd will not launch a second copy of a job while one is still alive, that
# one hang silently suppressed ~2 days of scheduled runs. A normal full run
# finishes in well under a minute.
MAX_RUNTIME=600

# Run "$@" but SIGTERM (then SIGKILL) it if it outlives $1 seconds. launchd's
# minimal PATH has no GNU `timeout`, so we roll our own with a watchdog subshell.
run_with_timeout() {
  local limit=$1; shift
  "$@" &
  local cmd_pid=$!
  (
    sleep "$limit"
    print -r -- "✗ Sync exceeded ${limit}s wall-clock limit — killing (hang guard)." \
      >> "${LOG_DIR}/err.log"
    kill -TERM "$cmd_pid" 2>/dev/null
    sleep 10
    kill -KILL "$cmd_pid" 2>/dev/null
  ) &
  local watch_pid=$!
  wait "$cmd_pid"
  local rc=$?
  # Sync finished on its own — cancel the watchdog so it doesn't linger.
  kill "$watch_pid" 2>/dev/null
  wait "$watch_pid" 2>/dev/null
  return $rc
}

mkdir -p "$LOG_DIR"
rm -f "$HEARTBEAT_MARKER"
cd "$REPO_DIR" || exit 78

fail() {
  print -r -- "$1" | tee "$CRASH_LOG" >&2
  "$PYTHON" "${REPO_DIR}/report_crash.py" "${2:-1}" "$CRASH_LOG" || \
    print -r -- "⚠ crash reporter also failed" >&2
  exit "${2:-1}"
}

case "$REPO_DIR" in
  */Documents/*|*/Desktop/*)
    fail "✗ Repo sits under an iCloud-synced path (${REPO_DIR}); files will be evicted and background runs will fail." 78
    ;;
esac

for f in run_today_prod.py config.py tastytrade_client.py \
         transaction_processor.py spreadsheet_logger.py .env \
         google-sheets-credentials.json; do
  if ! head -c 1 "${REPO_DIR}/${f}" > /dev/null 2>&1; then
    fail "✗ Cannot read ${f} — file missing, unreadable, or evicted to a cloud stub." 78
  fi
done

run_with_timeout "$MAX_RUNTIME" "$PYTHON" "${REPO_DIR}/run_today_prod.py"
# NB: not `status` — that name is a read-only special variable in zsh (an alias
# for $?), and assigning to it aborts the script.
sync_status=$?

# run_today_prod.py writes its own Sync Log row for both success and handled
# errors, touching the marker when it does. Only report here when the run
# failed and left no marker — i.e. it died before reaching its own reporting,
# the silent-failure case this wrapper exists for.
if [[ $sync_status -ne 0 && ! -f "$HEARTBEAT_MARKER" ]]; then
  tail -40 "${LOG_DIR}/err.log" > "$CRASH_LOG" 2>/dev/null
  "$PYTHON" "${REPO_DIR}/report_crash.py" "$sync_status" "$CRASH_LOG" || \
    print -r -- "⚠ crash reporter also failed" >&2
fi

exit $sync_status
