#!/usr/bin/env bash
# Stop everything start.sh started, and leave the data directories in place.
# The data is kept because a demo that went wrong is worth reading afterwards,
# and .local/.gitignore already keeps it out of the repository.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../../.." && pwd)"

stopped=0
for pidfile in "${ROOT}"/.local/demo/*/server.pid "${ROOT}"/.local/demo/*/client.pid; do
  [ -f "${pidfile}" ] || continue
  pid="$(cat "${pidfile}")"
  if kill "${pid}" 2>/dev/null; then
    printf 'stopped pid %s (%s)\n' "${pid}" "${pidfile#"${ROOT}/"}"
    stopped=$((stopped + 1))
  fi
  rm -f "${pidfile}"
done

[ "${stopped}" -gt 0 ] || printf 'nothing to stop.\n'
