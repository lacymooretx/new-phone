from pydantic import BaseModel


class StartCallRequest(BaseModel):
    call_id: str
    tenant_id: str
    context_name: str
    caller_number: str | None = None
    caller_name: str | None = None
    # Full config pushed by main API
    provider_mode: str = "monolithic"  # "monolithic" | "pipeline"
    provider_name: str = ""  # e.g., "openai_realtime", "deepgram"
    api_key: str = ""
    model_id: str | None = None
    base_url: str | None = None
    system_prompt: str = ""
    greeting: str = ""
    voice_id: str | None = None
    language: str = "en-US"
    tools: list[str] = []  # tool names to enable
    barge_in_enabled: bool = True
    silence_timeout_ms: int = 5000
    # Pipeline-specific
    pipeline_stt: str | None = None
    pipeline_llm: str | None = None
    pipeline_tts: str | None = None
    stt_api_key: str | None = None
    llm_api_key: str | None = None
    tts_api_key: str | None = None


class StopCallRequest(BaseModel):
    call_id: str


class CallStatusResponse(BaseModel):
    status: str
    call_id: str
    provider: str | None = None
    duration_seconds: int = 0
    turn_count: int = 0


class TestProviderRequest(BaseModel):
    provider_name: str
    api_key: str
    model_id: str | None = None
    base_url: str | None = None


class TestContextRequest(BaseModel):
    system_prompt: str
    message: str
    provider_name: str = "openai"
    api_key: str = ""
    model_id: str | None = None
