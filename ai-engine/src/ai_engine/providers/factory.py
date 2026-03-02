"""Provider factory — creates provider instances by name."""

from __future__ import annotations

from ai_engine.providers.base import AIProviderInterface, ProviderType


def create_provider(provider_name: str) -> AIProviderInterface:
    """Create a provider instance by name.

    Args:
        provider_name: One of "openai_realtime", "deepgram", "google_live", "elevenlabs"

    Returns:
        An instance of the requested provider.

    Raises:
        ValueError: If the provider name is unknown.
    """
    if provider_name == ProviderType.OPENAI_REALTIME:
        from ai_engine.providers.openai_realtime import OpenAIRealtimeProvider

        return OpenAIRealtimeProvider()

    if provider_name == ProviderType.DEEPGRAM:
        from ai_engine.providers.deepgram import DeepgramProvider

        return DeepgramProvider()

    if provider_name == ProviderType.GOOGLE_LIVE:
        from ai_engine.providers.google_live import GoogleLiveProvider

        return GoogleLiveProvider()

    if provider_name == ProviderType.ELEVENLABS:
        from ai_engine.providers.elevenlabs import ElevenLabsProvider

        return ElevenLabsProvider()

    if provider_name == "pipeline":
        from ai_engine.providers.pipeline_provider import PipelineProvider

        return PipelineProvider()

    raise ValueError(f"Unknown provider: {provider_name}")
