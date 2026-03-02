"""Tests for ai_engine.providers.factory — provider dispatch."""

from __future__ import annotations

import pytest
from ai_engine.providers.base import AIProviderInterface
from ai_engine.providers.factory import create_provider


class TestCreateProvider:
    def test_openai_realtime(self):
        p = create_provider("openai_realtime")
        assert isinstance(p, AIProviderInterface)
        assert p.name == "openai_realtime"

    def test_deepgram(self):
        p = create_provider("deepgram")
        assert isinstance(p, AIProviderInterface)
        assert p.name == "deepgram"

    def test_google_live(self):
        p = create_provider("google_live")
        assert isinstance(p, AIProviderInterface)
        assert p.name == "google_live"

    def test_elevenlabs(self):
        p = create_provider("elevenlabs")
        assert isinstance(p, AIProviderInterface)
        assert p.name == "elevenlabs"

    def test_pipeline(self):
        p = create_provider("pipeline")
        assert isinstance(p, AIProviderInterface)
        assert p.name == "pipeline"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("nonexistent_provider")
