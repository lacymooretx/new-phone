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

# Enable TLS on external profile so outbound SIP trunks can use TLS transport.
# ClearlyIP and other providers require TLS for SIP registration.
sed -i 's/external_ssl_enable=false/external_ssl_enable=true/' /etc/freeswitch/vars.xml
echo "Enabled TLS on external profile"

# Remove any standalone TLS profile — the internal profile handles TLS/WSS.
# A separate tls.xml steals the WSS port and lacks auth/registration config.
rm -f /etc/freeswitch/sip_profiles/tls.xml
echo "Removed standalone TLS profile (internal handles WSS)"

# Include gateway XML files from the shared /gateways/ volume in the external profile.
# The API writes individual gateway files there; FS picks them up via reloadxml + rescan.
# FS X-PRE-PROCESS only supports paths relative to /etc/freeswitch, so we create a
# symlink from sip_profiles/gateways -> /gateways and use a relative include.
ln -sfn /gateways /etc/freeswitch/sip_profiles/gateways
echo "Linked /etc/freeswitch/sip_profiles/gateways -> /gateways"

# Replace any old absolute /gateways/ include with relative path
if [ -f /etc/freeswitch/sip_profiles/external.xml ]; then
    sed -i 's|data="/gateways/\*\.xml"|data="gateways/*.xml"|' /etc/freeswitch/sip_profiles/external.xml
fi

if [ -f /etc/freeswitch/sip_profiles/external.xml ] && ! grep -q 'data="gateways/' /etc/freeswitch/sip_profiles/external.xml; then
    sed -i 's|<gateways>|<gateways>\n      <X-PRE-PROCESS cmd="include" data="gateways/*.xml"/>|' /etc/freeswitch/sip_profiles/external.xml
    echo "Added gateways/*.xml include to external profile"
fi

# Bind external profile to 0.0.0.0 for outbound calls through Docker bridge networks.
sed -i 's|<param name="sip-ip" value="\$\${local_ip_v4}"/>|<param name="sip-ip" value="0.0.0.0"/>|' /etc/freeswitch/sip_profiles/external.xml
sed -i 's|<param name="rtp-ip" value="\$\${local_ip_v4}"/>|<param name="rtp-ip" value="0.0.0.0"/>|' /etc/freeswitch/sip_profiles/external.xml
echo "Bound external profile to 0.0.0.0"

# Set RTP port range to match Docker exposed ports (16384-16884).
# The vanilla config has these commented out, defaulting to 16384-32768.
sed -i 's|<!-- <param name="rtp-start-port" value="16384"/> -->|<param name="rtp-start-port" value="16384"/>|' /etc/freeswitch/autoload_configs/switch.conf.xml
sed -i 's|<!-- <param name="rtp-end-port" value="32768"/> -->|<param name="rtp-end-port" value="16884"/>|' /etc/freeswitch/autoload_configs/switch.conf.xml
echo "Set RTP port range to 16384-16884"

# Bind SIP/RTP to all interfaces (0.0.0.0) so FreeSWITCH is reachable from
# Docker bridge containers (web nginx WSS proxy, API ESL) while still
# advertising the public IP via ext-rtp-ip/ext-sip-ip for external clients.
# Vanilla config uses $${local_ip_v4} which only binds to the primary interface.
sed -i 's|<param name="sip-ip" value="\$\${local_ip_v4}"/>|<param name="sip-ip" value="0.0.0.0"/>|' /etc/freeswitch/sip_profiles/internal.xml
sed -i 's|<param name="rtp-ip" value="\$\${local_ip_v4}"/>|<param name="rtp-ip" value="0.0.0.0"/>|' /etc/freeswitch/sip_profiles/internal.xml
echo "Bound internal profile to 0.0.0.0"

# Filter ICE candidates to only include public IPs (wan_v4.auto denies
# RFC1918 ranges). With rtp-ip=0.0.0.0, candidates for all interfaces
# are generated; this ACL ensures only the public IP is advertised.
sed -i '/<param name="ext-rtp-ip"/a\    <param name="apply-candidate-acl" value="wan_v4.auto"/>' /etc/freeswitch/sip_profiles/internal.xml
echo "Added apply-candidate-acl for WebRTC ICE candidates"

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
# Do NOT use -nonat: it disables NAT traversal which prevents FreeSWITCH
# from generating external IP candidates for WebRTC ICE behind Docker NAT.
/usr/bin/freeswitch -nc -nf &
pid="$!"
wait $pid
exit 0
