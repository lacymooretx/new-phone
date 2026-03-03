#!/bin/sh
set -e

# Resolve freeswitch IP from /etc/hosts (populated by extra_hosts in docker-compose).
# With host networking on FreeSWITCH, Docker DNS (127.0.0.11) can't resolve it,
# so we substitute the IP directly into the nginx config at startup.
FS_IP=$(awk '/[[:space:]]freeswitch/ {print $1; exit}' /etc/hosts 2>/dev/null || true)

if [ -n "$FS_IP" ]; then
    sed -i 's|resolver 127.0.0.11 valid=10s;||' /etc/nginx/conf.d/default.conf
    sed -i "s|https://freeswitch:7443|https://${FS_IP}:7443|" /etc/nginx/conf.d/default.conf
    echo "nginx: resolved freeswitch -> ${FS_IP}"
fi

exec "$@"
