"""Jinja2-based phone configuration builder."""

from __future__ import annotations

import hashlib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from new_phone.models.device import Device, DeviceKey
from new_phone.models.extension import Extension
from new_phone.models.phone_model import PhoneModel
from new_phone.models.tenant import Tenant

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env: Environment | None = None


def _get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
            keep_trailing_newline=True,
        )
    return _env


# Yealink key type codes (numeric DSS key types)
YEALINK_KEY_TYPE_MAP = {
    "line": 15,
    "blf": 16,
    "speed_dial": 13,
    "dtmf": 17,
    "park": 10,
    "intercom": 30,
    "none": 0,
}

# Sangoma key type names (XML string values)
SANGOMA_KEY_TYPE_MAP = {
    "line": "line",
    "blf": "blf",
    "speed_dial": "speed_dial",
    "dtmf": "dtmf",
    "park": "park",
    "intercom": "intercom",
    "none": "none",
}

# Map manufacturer to template prefix and key type map
MANUFACTURER_CONFIG = {
    "yealink": {
        "template_prefix": "yealink",
        "base_template": "base.cfg.j2",
        "keys_template": "keys.cfg.j2",
        "key_type_map": YEALINK_KEY_TYPE_MAP,
        "content_type": "text/plain",
    },
    "sangoma": {
        "template_prefix": "sangoma",
        "base_template": "base.cfg.xml.j2",
        "keys_template": "keys.cfg.xml.j2",
        "key_type_map": SANGOMA_KEY_TYPE_MAP,
        "content_type": "application/xml",
    },
}


def _get_manufacturer_config(phone_model: PhoneModel) -> dict:
    """Get the template config for a phone model's manufacturer."""
    manufacturer_key = phone_model.manufacturer.lower()
    if manufacturer_key in MANUFACTURER_CONFIG:
        return MANUFACTURER_CONFIG[manufacturer_key]
    # Default to Yealink-style config for unknown manufacturers
    return MANUFACTURER_CONFIG["yealink"]


def build_config(
    device: Device,
    extension: Extension | None,
    tenant: Tenant,
    phone_model: PhoneModel,
    keys: list[DeviceKey],
    sip_password: str | None,
    sip_server: str,
    ntp_server: str = "pool.ntp.org",
    timezone: str = "America/New_York",
) -> tuple[str, str]:
    """Render a phone configuration for the given device.

    Returns (config_text, sha256_hash).
    """
    env = _get_env()
    mfg_config = _get_manufacturer_config(phone_model)

    template_prefix = mfg_config["template_prefix"]
    base_template = env.get_template(f"{template_prefix}/{mfg_config['base_template']}")
    keys_template = env.get_template(f"{template_prefix}/{mfg_config['keys_template']}")

    # Separate line keys from expansion keys
    line_keys = sorted(
        [k for k in keys if k.key_section == "line_key"],
        key=lambda k: k.key_index,
    )
    expansion_keys = sorted(
        [k for k in keys if k.key_section.startswith("expansion_")],
        key=lambda k: (k.key_section, k.key_index),
    )

    sip_domain = tenant.sip_domain or f"{tenant.slug}.sip.local"

    context = {
        "device": device,
        "extension": extension,
        "tenant": tenant,
        "phone_model": phone_model,
        "sip_password": sip_password,
        "sip_domain": sip_domain,
        "sip_server": sip_server,
        "ntp_server": ntp_server,
        "timezone": timezone,
        "line_keys": line_keys,
        "expansion_keys": expansion_keys,
        "key_type_map": mfg_config["key_type_map"],
    }

    base_cfg = base_template.render(**context)
    keys_cfg = keys_template.render(**context)

    full_config = base_cfg + "\n" + keys_cfg
    config_hash = hashlib.sha256(full_config.encode()).hexdigest()

    return full_config, config_hash


def get_content_type(phone_model: PhoneModel) -> str:
    """Return the appropriate HTTP content type for a phone model's config format."""
    mfg_config = _get_manufacturer_config(phone_model)
    return mfg_config["content_type"]
