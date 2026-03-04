# FreeSWITCH xml_curl Configuration Binding: Sofia Gateways

Research date: 2026-03-03

## Overview

There are **two separate mechanisms** for dynamically loading gateways via xml_curl:

1. **Configuration binding** (`section=configuration`) — serves the entire `sofia.conf` including profiles and gateways
2. **Directory binding** (`section=directory`, `purpose=gateways`) — serves gateways embedded in user/domain directory entries

This document covers both, with emphasis on the configuration binding approach since that is the simpler and recommended path for SIP trunk gateways.

---

## 1. Does `sofia profile external rescan` Trigger an xml_curl Configuration Request?

**Yes.** When FreeSWITCH executes `sofia profile external rescan` (or `sofia profile external rescan reloadxml`), it re-reads the sofia.conf configuration. If mod_xml_curl is bound to the `configuration` section, FreeSWITCH will POST to your xml_curl gateway URL requesting `sofia.conf`.

**Critical prerequisite:** `mod_xml_curl` must be loaded **before** `mod_sofia` in `modules.conf.xml`. If mod_sofia loads first, it reads static XML before xml_curl is available, and you will never see configuration requests for sofia.conf.

### Rescan vs Restart

- **rescan** — loads new gateways without disrupting existing calls. Does NOT reload profile settings like sip-ip or sip-port.
- **restart** — tears down the profile entirely and rebuilds it. Drops all active calls on that profile.

### Updating Existing Gateways

Rescan only adds **new** gateways. To update an existing gateway:

```
sofia profile external killgw <gateway_name>
sofia profile external rescan reloadxml
```

---

## 2. POST Parameters Sent by FreeSWITCH

### Configuration Binding Request (for sofia.conf)

When FreeSWITCH requests sofia.conf via xml_curl, it POSTs:

| Parameter | Value | Description |
|-----------|-------|-------------|
| `section` | `configuration` | The XML section being requested |
| `tag_name` | `configuration` | XML tag name |
| `key_name` | `name` | The attribute name to match |
| `key_value` | `sofia.conf` | The config file being requested |
| `hostname` | (system hostname) | FreeSWITCH hostname |
| `Core-UUID` | (uuid) | FreeSWITCH instance UUID |
| `FreeSWITCH-Hostname` | (hostname) | |
| `FreeSWITCH-IPv4` | (ip) | |
| `FreeSWITCH-IPv6` | (ip) | |
| `Event-Name` | `REQUEST_PARAMS` | |
| `Event-Date-Local` | (timestamp) | |
| `Event-Date-GMT` | (timestamp) | |
| `Event-Calling-File` | `sofia.c` | Source file making the request |
| `Event-Calling-Function` | (function name) | |

**The key discriminator is `key_value=sofia.conf`** — this tells your backend which configuration file FreeSWITCH wants.

### Directory Binding Request (purpose=gateways)

This is the **separate** directory-based gateway mechanism. When a sofia profile has `parse="true"` on its domain, FreeSWITCH sends a directory request:

| Parameter | Value |
|-----------|-------|
| `section` | `directory` |
| `purpose` | `gateways` |
| `profile` | (profile name, e.g., `external`) |

---

## 3. XML Response Format for Configuration Binding

### The Complete, Correct Format

The response must provide the **entire** sofia.conf configuration, wrapped in a `<document>` element. **xml_curl responses OVERRIDE static XML — they do not merge with it.**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<document type="freeswitch/xml">
  <section name="configuration">
    <configuration name="sofia.conf" description="sofia Endpoint">

      <global_settings>
        <param name="log-level" value="0"/>
        <param name="debug-presence" value="0"/>
      </global_settings>

      <profiles>
        <profile name="external">
          <gateways>
            <gateway name="trunk_clearlyip_1">
              <param name="username" value="my_username"/>
              <param name="password" value="my_password"/>
              <param name="realm" value="sip.clearlyip.com"/>
              <param name="proxy" value="sip.clearlyip.com"/>
              <param name="register" value="true"/>
              <param name="expire-seconds" value="3600"/>
              <param name="retry-seconds" value="30"/>
              <param name="ping" value="25"/>
              <param name="caller-id-in-from" value="false"/>
              <param name="contact-params" value="tport=tls"/>
              <param name="register-transport" value="tls"/>
            </gateway>
            <gateway name="trunk_twilio_1">
              <param name="username" value="twilio_user"/>
              <param name="password" value="twilio_pass"/>
              <param name="realm" value="pstn.twilio.com"/>
              <param name="proxy" value="pstn.twilio.com"/>
              <param name="register" value="false"/>
              <param name="caller-id-in-from" value="true"/>
            </gateway>
          </gateways>

          <aliases>
          </aliases>

          <domains>
            <domain name="all" alias="false" parse="false"/>
          </domains>

          <settings>
            <param name="context" value="public"/>
            <param name="dialplan" value="XML"/>
            <param name="sip-ip" value="$${local_ip_v4}"/>
            <param name="sip-port" value="5080"/>
            <param name="rtp-ip" value="$${local_ip_v4}"/>
            <param name="ext-rtp-ip" value="$${external_rtp_ip}"/>
            <param name="ext-sip-ip" value="$${external_sip_ip}"/>
            <param name="inbound-codec-prefs" value="$${global_codec_prefs}"/>
            <param name="outbound-codec-prefs" value="$${global_codec_prefs}"/>
            <param name="manage-presence" value="false"/>
            <param name="auth-calls" value="false"/>
            <param name="tls" value="true"/>
            <param name="tls-bind-params" value="transport=tls"/>
            <param name="tls-sip-port" value="5081"/>
            <param name="tls-cert-dir" value="$${base_dir}/certs"/>
          </settings>
        </profile>

        <!-- Additional profiles as needed -->
        <profile name="internal">
          <gateways/>
          <aliases/>
          <domains>
            <domain name="all" alias="true" parse="false"/>
          </domains>
          <settings>
            <param name="context" value="default"/>
            <param name="dialplan" value="XML"/>
            <param name="sip-ip" value="$${local_ip_v4}"/>
            <param name="sip-port" value="5060"/>
            <param name="rtp-ip" value="$${local_ip_v4}"/>
            <param name="inbound-codec-prefs" value="$${global_codec_prefs}"/>
            <param name="outbound-codec-prefs" value="$${global_codec_prefs}"/>
            <param name="auth-calls" value="true"/>
            <param name="manage-presence" value="true"/>
          </settings>
        </profile>
      </profiles>

    </configuration>
  </section>
</document>
```

### Not Found Response

If you cannot serve the requested configuration, return:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<document type="freeswitch/xml">
  <section name="result">
    <result status="not found" />
  </section>
</document>
```

This tells FreeSWITCH to fall back to static XML files on disk.

---

## 4. Nesting Hierarchy

The complete nesting for the configuration binding is:

```
<document type="freeswitch/xml">
  <section name="configuration">
    <configuration name="sofia.conf" description="sofia Endpoint">
      <global_settings>
        <param .../>
      </global_settings>
      <profiles>
        <profile name="external">
          <gateways>
            <gateway name="gw1">
              <param .../>
            </gateway>
          </gateways>
          <aliases/>
          <domains>
            <domain .../>
          </domains>
          <settings>
            <param .../>
          </settings>
        </profile>
      </profiles>
    </configuration>
  </section>
</document>
```

**Key points:**
- YES, it expects `<profiles>` wrapping `<profile name="external">`
- YES, `<gateways>` goes inside the `<profile>`, not standalone
- You MUST include `<settings>` with at least `sip-ip`, `sip-port`, and `context` — incomplete profiles are silently ignored
- You MUST return the ENTIRE sofia.conf — it replaces the static file entirely, it does NOT merge

---

## 5. Directory-Based Gateway Alternative (purpose=gateways)

There is an alternative mechanism where gateways are defined in the **directory** section (per-user), not the configuration section. This is triggered when:

1. A sofia profile has `<domain name="..." parse="true"/>` in its `<domains>` section
2. FreeSWITCH sends a directory request with `purpose=gateways` and `profile=<name>`

The XML response for this mechanism looks different:

```xml
<document type="freeswitch/xml">
  <section name="directory">
    <domain name="example.com">
      <user id="gateway_user">
        <gateways>
          <gateway name="my_gw">
            <param name="username" value="user"/>
            <param name="password" value="pass"/>
            <param name="realm" value="sip.provider.com"/>
            <param name="proxy" value="sip.provider.com"/>
            <param name="register" value="true"/>
          </gateway>
        </gateways>
        <params>
          <param name="password" value="dummy"/>
        </params>
      </user>
    </domain>
  </section>
</document>
```

**This approach is NOT recommended for SIP trunk gateways** — Brian West (FreeSWITCH core dev) recommends putting trunk gateways directly in the profile's `<gateways>` section, especially for large deployments. The directory-based approach is more suited for per-user gateway registrations.

---

## 6. Recommended Approach for Our Platform

For the new-phone platform's dynamic SIP trunk provisioning:

1. **Use the configuration binding** (`section=configuration`, `key_value=sofia.conf`)
2. Return the **complete** sofia.conf with all profiles and their gateways
3. When a tenant's trunk config changes:
   - API calls `sofia profile external killgw <gw_name>` via ESL
   - API calls `sofia profile external rescan reloadxml` via ESL
   - FreeSWITCH re-requests sofia.conf from our API
   - Our API returns updated XML with the new/modified gateway
4. Set `parse="false"` on domains to avoid the directory gateway mechanism

---

## 7. Gateway Parameter Reference

Common gateway parameters:

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `username` | Yes* | — | SIP auth username |
| `password` | Yes* | — | SIP auth password |
| `realm` | No | gateway name | Auth realm |
| `proxy` | No | realm value | SIP proxy host:port |
| `register` | No | `true` | Whether to REGISTER |
| `expire-seconds` | No | `3600` | Registration expiry |
| `retry-seconds` | No | `30` | Retry interval on failure |
| `ping` | No | `0` | OPTIONS ping interval (seconds) |
| `caller-id-in-from` | No | `false` | Put caller ID in From header |
| `from-user` | No | username | From header user |
| `from-domain` | No | realm | From header domain |
| `extension` | No | username | Dest for inbound calls |
| `register-transport` | No | `udp` | Transport: udp, tcp, tls |
| `contact-params` | No | — | Extra Contact header params |
| `outbound-proxy` | No | — | Outbound proxy |

*Not required for register=false trunks that use IP auth.

---

## Sources

- [mod_xml_curl Documentation](https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Modules/mod_xml_curl_1049001/)
- [Sofia Configuration Files](https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Configuration/Sofia-SIP-Stack/Sofia-Configuration-Files_7144453/)
- [Gateways Configuration](https://developer.signalwire.com/freeswitch/FreeSWITCH-Explained/Configuration/Sofia-SIP-Stack/Gateways-Configuration_7144069/)
- [FreeSWITCH sofia.conf.xml source](https://github.com/signalwire/freeswitch/blob/master/src/mod/endpoints/mod_sofia/conf/sofia.conf.xml)
- [FreeSWITCH mailing list discussions on xml_curl gateways](https://freeswitch-users.freeswitch.narkive.com/QyDFVFHu/xml-curl-gateways)
