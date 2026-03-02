import json
import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.encryption import decrypt_value
from new_phone.db.rls import set_tenant_context
from new_phone.models.ai_agent_conversation import AIAgentConversation
from new_phone.models.ai_agent_provider_config import AIAgentProviderConfig
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.compliance_monitoring import (
    ComplianceEvaluation,
    ComplianceEvaluationStatus,
    ComplianceRule,
    ComplianceRuleResult,
    ComplianceRuleResultValue,
    ComplianceRuleScopeType,
    ComplianceRuleSeverity,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a compliance evaluator for a call center. You will be given a call transcript and a list of compliance rules. For each rule, evaluate whether the agent in the transcript followed the rule.

For each rule, respond with:
- rule_name: the exact rule name provided
- result: "pass" if the rule was followed, "fail" if it was violated, "not_applicable" if the rule does not apply to this conversation
- explanation: brief explanation of your assessment
- evidence: quote the relevant part of the transcript that supports your assessment, or null if not applicable

Respond with a JSON array of objects. Example:
[
  {"rule_name": "Greeting", "result": "pass", "explanation": "Agent greeted the caller by name.", "evidence": "Hello John, thank you for calling."},
  {"rule_name": "Disclosure", "result": "fail", "explanation": "Agent did not disclose the call is being recorded.", "evidence": null}
]

IMPORTANT: Respond ONLY with the JSON array, no other text."""


class ComplianceScanService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(
        self,
        tenant_id: uuid.UUID,
        *,
        cdr_id: uuid.UUID | None = None,
        ai_conversation_id: uuid.UUID | None = None,
    ) -> ComplianceEvaluation:
        await set_tenant_context(self.db, tenant_id)

        # 1. Resolve transcript
        transcript_text, conversation, cdr = await self._resolve_transcript(
            tenant_id, cdr_id, ai_conversation_id
        )

        # Create evaluation record
        evaluation = ComplianceEvaluation(
            tenant_id=tenant_id,
            cdr_id=cdr.id if cdr else cdr_id,
            ai_conversation_id=conversation.id if conversation else ai_conversation_id,
            transcript_text=transcript_text,
            status=ComplianceEvaluationStatus.PENDING,
        )
        self.db.add(evaluation)
        await self.db.flush()

        try:
            # 2. Get applicable rules
            rules = await self._get_applicable_rules(tenant_id, conversation, cdr)
            if not rules:
                evaluation.status = ComplianceEvaluationStatus.COMPLETED
                evaluation.overall_score = 100.0
                evaluation.evaluated_at = datetime.now(UTC)
                await self.db.flush()
                return evaluation

            # 3. Find LLM provider
            provider_name, api_key, model_id = await self._get_llm_provider(tenant_id)
            evaluation.provider_name = provider_name

            # 4. Call LLM
            llm_results = await self._call_llm(
                provider_name, api_key, model_id, transcript_text, rules
            )

            # 5. Create rule results and compute score
            await self._process_results(tenant_id, evaluation, rules, llm_results)

            evaluation.status = ComplianceEvaluationStatus.COMPLETED
            evaluation.evaluated_at = datetime.now(UTC)

        except Exception as e:
            logger.error("Compliance evaluation failed: %s", str(e), exc_info=True)
            evaluation.status = ComplianceEvaluationStatus.FAILED
            evaluation.evaluated_at = datetime.now(UTC)
            await self.db.flush()
            return evaluation

        # 6. Update CDR if linked
        if cdr:
            cdr.compliance_score = evaluation.overall_score
            cdr.compliance_evaluation_id = evaluation.id

        await self.db.flush()
        await self.db.refresh(evaluation)
        return evaluation

    async def _resolve_transcript(
        self,
        tenant_id: uuid.UUID,
        cdr_id: uuid.UUID | None,
        ai_conversation_id: uuid.UUID | None,
    ) -> tuple[str, AIAgentConversation | None, CallDetailRecord | None]:
        conversation: AIAgentConversation | None = None
        cdr: CallDetailRecord | None = None

        if ai_conversation_id:
            result = await self.db.execute(
                select(AIAgentConversation).where(
                    AIAgentConversation.tenant_id == tenant_id,
                    AIAgentConversation.id == ai_conversation_id,
                )
            )
            conversation = result.scalar_one_or_none()
            if not conversation:
                raise ValueError("AI conversation not found")
            # Also load CDR if linked
            if conversation.cdr_id:
                cdr_result = await self.db.execute(
                    select(CallDetailRecord).where(
                        CallDetailRecord.id == conversation.cdr_id
                    )
                )
                cdr = cdr_result.scalar_one_or_none()

        elif cdr_id:
            cdr_result = await self.db.execute(
                select(CallDetailRecord).where(
                    CallDetailRecord.tenant_id == tenant_id,
                    CallDetailRecord.id == cdr_id,
                )
            )
            cdr = cdr_result.scalar_one_or_none()
            if not cdr:
                raise ValueError("CDR not found")
            # Find AI conversation linked to this CDR
            conv_result = await self.db.execute(
                select(AIAgentConversation).where(
                    AIAgentConversation.tenant_id == tenant_id,
                    AIAgentConversation.cdr_id == cdr_id,
                )
            )
            conversation = conv_result.scalar_one_or_none()
            if not conversation:
                raise ValueError("No AI conversation found for this CDR")

        if not conversation:
            raise ValueError("Could not resolve transcript source")

        transcript_text = self._flatten_transcript(conversation.transcript)
        return transcript_text, conversation, cdr

    @staticmethod
    def _flatten_transcript(transcript: dict | list) -> str:
        lines = []
        entries = transcript if isinstance(transcript, list) else transcript.get("messages", [])
        for entry in entries:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            label = "[Agent]" if role in ("assistant", "agent", "bot") else "[Caller]"
            lines.append(f"{label}: {content}")
        return "\n".join(lines)

    async def _get_applicable_rules(
        self,
        tenant_id: uuid.UUID,
        conversation: AIAgentConversation | None,
        cdr: CallDetailRecord | None,
    ) -> list[ComplianceRule]:
        stmt = select(ComplianceRule).where(
            ComplianceRule.tenant_id == tenant_id,
            ComplianceRule.is_active.is_(True),
        )
        result = await self.db.execute(stmt)
        all_rules = list(result.scalars().all())

        applicable = []
        for rule in all_rules:
            if rule.scope_type == ComplianceRuleScopeType.ALL:
                applicable.append(rule)
            elif rule.scope_type == ComplianceRuleScopeType.QUEUE and cdr and cdr.queue_id:
                if rule.scope_id == cdr.queue_id:
                    applicable.append(rule)
            elif rule.scope_type == ComplianceRuleScopeType.AGENT_CONTEXT and conversation and rule.scope_id == conversation.context_id:
                applicable.append(rule)
        return applicable

    async def _get_llm_provider(
        self, tenant_id: uuid.UUID
    ) -> tuple[str, str, str]:
        # Prefer anthropic > openai
        for provider in ["anthropic", "openai"]:
            result = await self.db.execute(
                select(AIAgentProviderConfig).where(
                    AIAgentProviderConfig.tenant_id == tenant_id,
                    AIAgentProviderConfig.provider_name == provider,
                    AIAgentProviderConfig.is_active.is_(True),
                )
            )
            config = result.scalar_one_or_none()
            if config and config.api_key_encrypted:
                api_key = decrypt_value(config.api_key_encrypted)
                model_id = config.model_id or (
                    "claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o-mini"
                )
                return provider, api_key, model_id

        raise ValueError("No active LLM provider configured for this tenant")

    async def _call_llm(
        self,
        provider_name: str,
        api_key: str,
        model_id: str,
        transcript_text: str,
        rules: list[ComplianceRule],
    ) -> list[dict]:
        rules_text = "\n".join(
            f"- **{rule.name}**: {rule.rule_text}" for rule in rules
        )
        user_message = f"## Compliance Rules\n{rules_text}\n\n## Call Transcript\n{transcript_text}"

        if provider_name == "anthropic":
            return await self._call_anthropic(api_key, model_id, user_message)
        else:
            return await self._call_openai(api_key, model_id, user_message)

    async def _call_anthropic(
        self, api_key: str, model_id: str, user_message: str
    ) -> list[dict]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model_id,
                    "max_tokens": 4096,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            response.raise_for_status()
            data = response.json()
            # Extract text from content blocks
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            return self._parse_llm_response(text)

    async def _call_openai(
        self, api_key: str, model_id: str, user_message: str
    ) -> list[dict]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_id,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            return self._parse_llm_response(text)

    @staticmethod
    def _parse_llm_response(text: str) -> list[dict]:
        text = text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            text = text.strip()

        parsed = json.loads(text)
        # OpenAI json_object mode may wrap in an object
        if isinstance(parsed, dict):
            for key in ("results", "evaluations", "rules"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            # If it's a single-key dict with a list value
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        if isinstance(parsed, list):
            return parsed
        raise ValueError(f"Unexpected LLM response format: {type(parsed)}")

    async def _process_results(
        self,
        tenant_id: uuid.UUID,
        evaluation: ComplianceEvaluation,
        rules: list[ComplianceRule],
        llm_results: list[dict],
    ) -> None:
        rule_map = {rule.name: rule for rule in rules}
        passed = 0
        failed = 0
        not_applicable = 0
        has_critical_failure = False

        for llm_result in llm_results:
            rule_name = llm_result.get("rule_name", "")
            result_value = llm_result.get("result", "not_applicable")

            # Normalize result value
            if result_value not in ("pass", "fail", "not_applicable"):
                result_value = "not_applicable"

            rule = rule_map.get(rule_name)

            rule_result = ComplianceRuleResult(
                tenant_id=tenant_id,
                evaluation_id=evaluation.id,
                rule_id=rule.id if rule else None,
                rule_name_snapshot=rule_name,
                rule_text_snapshot=rule.rule_text if rule else "",
                result=result_value,
                explanation=llm_result.get("explanation"),
                evidence=llm_result.get("evidence"),
            )
            self.db.add(rule_result)

            if result_value == ComplianceRuleResultValue.PASS:
                passed += 1
            elif result_value == ComplianceRuleResultValue.FAIL:
                failed += 1
                if rule and rule.severity == ComplianceRuleSeverity.CRITICAL:
                    has_critical_failure = True
            else:
                not_applicable += 1

        evaluation.rules_passed = passed
        evaluation.rules_failed = failed
        evaluation.rules_not_applicable = not_applicable
        evaluation.is_flagged = has_critical_failure

        # Score formula: (passed / (passed + failed)) * 100
        denominator = passed + failed
        if denominator > 0:
            evaluation.overall_score = round(passed / denominator * 100, 2)
        else:
            evaluation.overall_score = 100.0  # All rules were not_applicable

        await self.db.flush()
