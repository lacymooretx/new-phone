"""Factory for CRM provider instances."""

import json

from new_phone.auth.encryption import decrypt_value
from new_phone.integrations.crm.provider_base import CRMProviderBase
from new_phone.models.crm_config import CRMConfig, CRMProviderType


def get_crm_provider(config: CRMConfig) -> CRMProviderBase:
    """Instantiate the correct CRM provider from a CRMConfig model."""
    creds = json.loads(decrypt_value(config.encrypted_credentials))
    timeout = config.lookup_timeout_seconds

    if config.provider_type == CRMProviderType.SALESFORCE:
        from new_phone.integrations.crm.salesforce import SalesforceProvider

        return SalesforceProvider(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            username=creds["username"],
            password=creds["password"],
            security_token=creds["security_token"],
            base_url=config.base_url,
            timeout=timeout,
        )

    if config.provider_type == CRMProviderType.HUBSPOT:
        from new_phone.integrations.crm.hubspot import HubSpotProvider

        return HubSpotProvider(
            access_token=creds["access_token"],
            base_url=config.base_url,
            timeout=timeout,
        )

    if config.provider_type == CRMProviderType.CONNECTWISE:
        from new_phone.integrations.crm.connectwise_crm import ConnectWiseCRMProvider

        return ConnectWiseCRMProvider(
            company_id=creds["company_id"],
            public_key=creds["public_key"],
            private_key=creds["private_key"],
            client_id=creds["client_id"],
            base_url=config.base_url,
            timeout=timeout,
        )

    if config.provider_type == CRMProviderType.ZOHO:
        from new_phone.integrations.crm.zoho import ZohoProvider

        return ZohoProvider(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            refresh_token=creds["refresh_token"],
            api_domain=creds.get("api_domain"),
            base_url=config.base_url,
            timeout=timeout,
        )

    if config.provider_type == CRMProviderType.WEBHOOK:
        from new_phone.integrations.crm.webhook import WebhookProvider

        return WebhookProvider(
            url=creds["url"],
            auth_header=creds.get("auth_header", ""),
            timeout=timeout,
        )

    raise ValueError(f"Unknown CRM provider type: {config.provider_type}")
