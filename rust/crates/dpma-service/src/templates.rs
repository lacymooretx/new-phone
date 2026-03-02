use anyhow::{Context, Result};
use tera::Tera;

use crate::provisioning::PhoneConfig;

/// Template engine for generating Sangoma phone configuration XML.
pub struct PhoneTemplateEngine {
    tera: Tera,
}

impl PhoneTemplateEngine {
    /// Create a new template engine. If a template directory exists, load from there.
    /// Otherwise, use built-in default templates.
    pub fn new(template_dir: &str) -> Result<Self> {
        let mut tera = Tera::default();

        // Check if custom template directory exists
        let template_path = format!("{}/**/*.xml", template_dir);
        match Tera::new(&template_path) {
            Ok(custom_tera) => {
                tera.extend(&custom_tera).ok();
            }
            Err(_) => {
                tracing::info!("no custom templates found, using built-in defaults");
            }
        }

        // Register built-in default templates
        tera.add_raw_template("phone_config.xml", DEFAULT_PHONE_CONFIG_TEMPLATE)
            .context("failed to add default phone config template")?;

        tera.add_raw_template("account.xml", DEFAULT_ACCOUNT_TEMPLATE)
            .context("failed to add default account template")?;

        Ok(PhoneTemplateEngine { tera })
    }

    /// Render the full phone configuration XML for a given config.
    pub fn render_config(&self, config: &PhoneConfig) -> Result<String> {
        let mut context = tera::Context::new();

        context.insert("mac_address", &config.mac_address);
        context.insert("extension", &config.extension);
        context.insert("password", &config.password);
        context.insert("display_name", &config.display_name);
        context.insert("sip_server", &config.sip_server);
        context.insert("sip_port", &config.sip_port);
        context.insert("transport", &config.transport);
        context.insert("codecs", &config.codecs);
        context.insert("line_keys", &config.line_keys);
        context.insert("softkeys", &config.softkeys);
        context.insert("blf_keys", &config.blf_keys);
        context.insert("tls_enabled", &config.tls_enabled);
        context.insert("srtp_enabled", &config.srtp_enabled);

        self.tera
            .render("phone_config.xml", &context)
            .context("failed to render phone config template")
    }

    /// Render just the SIP account section.
    pub fn render_account(&self, config: &PhoneConfig) -> Result<String> {
        let mut context = tera::Context::new();

        context.insert("extension", &config.extension);
        context.insert("password", &config.password);
        context.insert("display_name", &config.display_name);
        context.insert("sip_server", &config.sip_server);
        context.insert("sip_port", &config.sip_port);
        context.insert("transport", &config.transport);
        context.insert("tls_enabled", &config.tls_enabled);
        context.insert("srtp_enabled", &config.srtp_enabled);

        self.tera
            .render("account.xml", &context)
            .context("failed to render account template")
    }
}

const DEFAULT_PHONE_CONFIG_TEMPLATE: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<PhoneConfig>
  <MAC>{{ mac_address }}</MAC>

  <Account>
    <AccountIndex>1</AccountIndex>
    <Enable>1</Enable>
    <Label>{{ display_name }}</Label>
    <DisplayName>{{ display_name }}</DisplayName>
    <AuthName>{{ extension }}</AuthName>
    <AuthPassword>{{ password }}</AuthPassword>
    <UserName>{{ extension }}</UserName>
    <SIPServer>{{ sip_server }}</SIPServer>
    <SIPPort>{{ sip_port }}</SIPPort>
    <Transport>{{ transport }}</Transport>
    {% if tls_enabled %}
    <TLSEnabled>1</TLSEnabled>
    {% else %}
    <TLSEnabled>0</TLSEnabled>
    {% endif %}
    {% if srtp_enabled %}
    <SRTPMode>2</SRTPMode>
    {% else %}
    <SRTPMode>0</SRTPMode>
    {% endif %}
  </Account>

  <Codecs>
    {% for codec in codecs %}
    <Codec>
      <Name>{{ codec }}</Name>
      <Priority>{{ loop.index }}</Priority>
    </Codec>
    {% endfor %}
  </Codecs>

  <LineKeys>
    {% for key in line_keys %}
    <Key>
      <Index>{{ key.index }}</Index>
      <Type>{{ key.key_type }}</Type>
      <Label>{{ key.label }}</Label>
      <Value>{{ key.value }}</Value>
    </Key>
    {% endfor %}
  </LineKeys>

  <SoftKeys>
    {% for key in softkeys %}
    <SoftKey>
      <Index>{{ key.index }}</Index>
      <Label>{{ key.label }}</Label>
      <Action>{{ key.action }}</Action>
    </SoftKey>
    {% endfor %}
  </SoftKeys>

  <BLFKeys>
    {% for key in blf_keys %}
    <BLFKey>
      <Index>{{ key.index }}</Index>
      <Extension>{{ key.extension }}</Extension>
      <Label>{{ key.label }}</Label>
    </BLFKey>
    {% endfor %}
  </BLFKeys>

  <Features>
    <DirectMedia>0</DirectMedia>
    <CallWaiting>1</CallWaiting>
    <DoNotDisturb>0</DoNotDisturb>
    <VoicemailExtension>*97</VoicemailExtension>
  </Features>
</PhoneConfig>
"#;

const DEFAULT_ACCOUNT_TEMPLATE: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<Account>
  <AccountIndex>1</AccountIndex>
  <Enable>1</Enable>
  <DisplayName>{{ display_name }}</DisplayName>
  <AuthName>{{ extension }}</AuthName>
  <AuthPassword>{{ password }}</AuthPassword>
  <UserName>{{ extension }}</UserName>
  <SIPServer>{{ sip_server }}</SIPServer>
  <SIPPort>{{ sip_port }}</SIPPort>
  <Transport>{{ transport }}</Transport>
  {% if tls_enabled %}
  <TLSEnabled>1</TLSEnabled>
  {% else %}
  <TLSEnabled>0</TLSEnabled>
  {% endif %}
  {% if srtp_enabled %}
  <SRTPMode>2</SRTPMode>
  {% else %}
  <SRTPMode>0</SRTPMode>
  {% endif %}
</Account>
"#;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::provisioning::PhoneConfig;

    #[test]
    fn test_render_config() {
        let engine = PhoneTemplateEngine::new("/nonexistent").unwrap();
        let config = PhoneConfig {
            mac_address: "aa:bb:cc:dd:ee:ff".to_string(),
            extension: "1001".to_string(),
            password: "secret123".to_string(),
            display_name: "Test User".to_string(),
            tenant_id: "tenant1".to_string(),
            sip_server: "pbx.example.com".to_string(),
            sip_port: 5061,
            transport: "TLS".to_string(),
            codecs: vec!["G722".to_string(), "PCMU".to_string()],
            line_keys: vec![],
            softkeys: vec![],
            blf_keys: vec![],
            tls_enabled: true,
            srtp_enabled: true,
        };

        let xml = engine.render_config(&config).unwrap();
        assert!(xml.contains("aa:bb:cc:dd:ee:ff"));
        assert!(xml.contains("1001"));
        assert!(xml.contains("Test User"));
        assert!(xml.contains("<TLSEnabled>1</TLSEnabled>"));
    }
}
