#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
temporary_dir="$(mktemp -d)"
session_name="codex-split-ci-${GITHUB_RUN_ID:-local}-$$"
status_file="$temporary_dir/status"
log_file="$temporary_dir/test.log"
config_file="$temporary_dir/config.kdl"

cleanup() {
  zellij kill-session "$session_name" >/dev/null 2>&1 || true
  rm -rf "$temporary_dir"
}
trap cleanup EXIT

cat > "$config_file" <<'KDL'
show_startup_tips false
show_release_notes false
default_mode "locked"
keybinds {
    unbind "Ctrl g"
    locked {
        bind "Ctrl Alt g" { SwitchToMode "Normal"; }
    }
    shared_except "locked" {
        bind "Ctrl Alt g" { SwitchToMode "Locked"; }
    }
}
KDL

# Variables in this single-quoted program expand in the background Zellij pane.
# shellcheck disable=SC2016
zellij --config "$config_file" attach --create-background "$session_name" \
  --close-on-exit -- bash -c '
    set +e
    cd "$1"
    timeout 60s python3 -m unittest discover -s tests -p test_zellij_integration.py -v > "$2" 2>&1
    result=$?
    printf "%s\n" "$result" > "$3"
    exit "$result"
  ' bash "$repo_root" "$log_file" "$status_file"

for _ in $(seq 1 75); do
  if [[ -s "$status_file" ]]; then
    break
  fi
  sleep 1
done

if [[ ! -s "$status_file" ]]; then
  cat "$log_file" 2>/dev/null || true
  echo "Zellij integration test did not finish within 75 seconds" >&2
  exit 1
fi

cat "$log_file"
result="$(cat "$status_file")"
if [[ "$result" != 0 ]] || grep -qi 'skipped' "$log_file"; then
  echo "Zellij integration test failed or was skipped" >&2
  exit 1
fi
