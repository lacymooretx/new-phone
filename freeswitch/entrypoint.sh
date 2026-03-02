#!/bin/sh
set -e

# Copy vanilla config if not already present
if [ ! -f "/etc/freeswitch/freeswitch.xml" ]; then
    mkdir -p /etc/freeswitch
    cp -arf /usr/share/freeswitch/conf/vanilla/* /etc/freeswitch/
    echo "Copied vanilla FreeSWITCH config"
fi

# Overlay custom configs (mounted at /custom-conf)
if [ -d /custom-conf ]; then
    cp -rf /custom-conf/* /etc/freeswitch/
    echo "Applied custom config overlay"
fi

# Install TLS certs (mounted at /custom-tls)
if [ -d /custom-tls ] && [ -f /custom-tls/agent.pem ]; then
    mkdir -p /etc/freeswitch/tls
    cp -f /custom-tls/agent.pem /etc/freeswitch/tls/agent.pem
    cp -f /custom-tls/cafile.pem /etc/freeswitch/tls/cafile.pem
    # wss.pem is an alias some FS builds look for
    cp -f /custom-tls/agent.pem /etc/freeswitch/tls/wss.pem
    chmod 600 /etc/freeswitch/tls/*.pem
    echo "Installed TLS certificates"
fi

# Trap SIGTERM for graceful shutdown
trap '/usr/bin/freeswitch -stop' SIGTERM

# Start FreeSWITCH
/usr/bin/freeswitch -nc -nf -nonat &
pid="$!"
wait $pid
exit 0
