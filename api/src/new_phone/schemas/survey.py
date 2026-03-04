import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SurveyQuestionSchema(BaseModel):
    question_text: str
    question_type: str = "rating"
    audio_prompt_id: str | None = None
    min_value: int = 1
    max_value: int = 5


class SurveyTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    intro_prompt: str | None = None
    thank_you_prompt: str | None = None
    questions: list[SurveyQuestionSchema] = Field(min_length=1)


class SurveyTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    intro_prompt: str | None = None
    thank_you_prompt: str | None = None
    questions: list[SurveyQuestionSchema] | None = None
    is_active: bool | None = None


class SurveyTemplateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    intro_prompt: str | None
    thank_you_prompt: str | None
    questions: list[dict]
    created_at: datetime
    updated_at: datetime


class SurveyResponseCreate(BaseModel):
    template_id: uuid.UUID
    queue_id: uuid.UUID | None = None
    agent_extension: str | None = None
    caller_number: str = Field(min_length=1, max_length=20)
    call_uuid: str | None = None
    answers: dict
    overall_score: float | None = None


class SurveyResponseResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    queue_id: uuid.UUID | None
    agent_extension: str | None
    caller_number: str
    call_uuid: str | None
    answers: dict
    overall_score: float | None
    completed_at: datetime | None
    created_at: datetime


class SurveyAnalytics(BaseModel):
    template_id: uuid.UUID
    template_name: str
    total_responses: int
    avg_overall_score: float | None
    per_question_avg: dict[str, float]
    per_queue_avg: dict[str, float]
    per_agent_avg: dict[str, float]
