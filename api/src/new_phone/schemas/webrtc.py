import uuid

from pydantic import BaseModel


class WebRTCCredentials(BaseModel):
    sip_username: str
    sip_password: str
    sip_domain: str
    wss_url: str
    extension_number: str
    extension_id: uuid.UUID
    display_name: str
