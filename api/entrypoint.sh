#!/bin/sh
set -e

# Fix gateway directory ownership — the Docker volume may be initialized
# by the FreeSWITCH container (running as root), making it unwritable by appuser.
# This runs as root before dropping to appuser via gosu/exec.
if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /gateways 2>/dev/null || true
    exec gosu appuser "$@"
else
    exec "$@"
fi
