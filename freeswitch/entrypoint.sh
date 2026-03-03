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

# Enable TLS on internal profile so it handles WSS (port 7443) for WebRTC.
# The vanilla config defaults to internal_ssl_enable=false.
sed -i 's/internal_ssl_enable=false/internal_ssl_enable=true/' /etc/freeswitch/vars.xml
echo "Enabled TLS on internal profile"

# Remove any standalone TLS profile — the internal profile handles TLS/WSS.
# A separate tls.xml steals the WSS port and lacks auth/registration config.
rm -f /etc/freeswitch/sip_profiles/tls.xml
echo "Removed standalone TLS profile (internal handles WSS)"

# Set RTP port range to match Docker exposed ports (16384-16884).
# The vanilla config has these commented out, defaulting to 16384-32768.
sed -i 's|<!-- <param name="rtp-start-port" value="16384"/> -->|<param name="rtp-start-port" value="16384"/>|' /etc/freeswitch/autoload_configs/switch.conf.xml
sed -i 's|<!-- <param name="rtp-end-port" value="32768"/> -->|<param name="rtp-end-port" value="16884"/>|' /etc/freeswitch/autoload_configs/switch.conf.xml
echo "Set RTP port range to 16384-16884"

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
