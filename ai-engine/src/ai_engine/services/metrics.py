"""Prometheus metrics for AI voice agent engine."""

from prometheus_client import Counter, Gauge, Histogram

# Active calls
ai_agent_active_calls = Gauge(
    "ai_agent_active_calls",
    "Number of currently active AI agent calls",
)

# Latency histograms
ai_agent_stt_latency_seconds = Histogram(
    "ai_agent_stt_latency_seconds",
    "STT processing latency in seconds",
    ["provider"],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0),
)

ai_agent_llm_latency_seconds = Histogram(
    "ai_agent_llm_latency_seconds",
    "LLM response latency in seconds",
    ["provider"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)

ai_agent_tts_latency_seconds = Histogram(
    "ai_agent_tts_latency_seconds",
    "TTS synthesis latency in seconds",
    ["provider"],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0),
)

ai_agent_turn_response_seconds = Histogram(
    "ai_agent_turn_response_seconds",
    "End-to-end turn response time in seconds",
    buckets=(0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0),
)

# Counters
ai_agent_barge_in_total = Counter(
    "ai_agent_barge_in_total",
    "Total number of barge-in events",
)

ai_agent_tool_calls_total = Counter(
    "ai_agent_tool_calls_total",
    "Total tool call executions",
    ["tool_name", "status"],
)

ai_agent_transfer_to_human_total = Counter(
    "ai_agent_transfer_to_human_total",
    "Total calls transferred to a human",
)

ai_agent_call_duration_seconds = Histogram(
    "ai_agent_call_duration_seconds",
    "AI agent call duration in seconds",
    buckets=(10, 30, 60, 120, 300, 600, 1800),
)

ai_agent_provider_errors_total = Counter(
    "ai_agent_provider_errors_total",
    "Total provider errors",
    ["provider"],
)
