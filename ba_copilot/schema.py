"""Output schema for BA Copilot.

The model must return data in exactly this shape (enforced through a forced
tool call), so every result can be validated, scored and exported.
"""

from typing import Literal

from pydantic import BaseModel, Field


class BusinessRule(BaseModel):
    id: str = Field(description="Unique ID, e.g. BR-1")
    rule: str = Field(description="The rule stated as a precise, testable sentence")
    source_quote: str = Field(description="Exact sentence from the requirement this rule comes from")


class OpenQuestion(BaseModel):
    id: str = Field(description="Unique ID, e.g. Q-1")
    question: str = Field(description="Question to ask business stakeholders")
    why_it_matters: str = Field(description="What could go wrong if this stays unanswered")
    category: Literal["eligibility", "limits", "process", "regulatory", "data", "integration", "ux", "other"]


class Risk(BaseModel):
    id: str = Field(description="Unique ID, e.g. R-1")
    description: str
    type: Literal["regulatory", "credit", "fraud", "operational", "technical", "data"]


class AcceptanceCriterion(BaseModel):
    id: str = Field(description="Unique ID tied to its story, e.g. AC-1.1")
    given: str
    when: str
    then: str


class UserStory(BaseModel):
    id: str = Field(description="Unique ID, e.g. US-1")
    as_a: str
    i_want: str
    so_that: str
    priority: Literal["Must", "Should", "Could"]
    source_quote: str = Field(description="Exact sentence from the requirement that motivates this story")
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)


class UatCase(BaseModel):
    id: str = Field(description="Unique ID, e.g. TC-1")
    title: str
    covers: list[str] = Field(min_length=1, description="IDs of acceptance criteria this test verifies")
    type: Literal["positive", "negative", "boundary"]
    preconditions: str
    steps: list[str] = Field(min_length=1)
    expected_result: str


class Analysis(BaseModel):
    summary: str = Field(description="Two or three sentences restating the requirement")
    business_rules: list[BusinessRule]
    open_questions: list[OpenQuestion]
    risks: list[Risk]
    stories: list[UserStory] = Field(min_length=1)
    uat_cases: list[UatCase] = Field(min_length=1)


def _inline_refs(schema: dict) -> dict:
    """Replace $ref pointers with their definitions so the tool schema is self-contained."""
    defs = schema.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                return resolve(dict(defs[name]))
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


def tool_input_schema() -> dict:
    return _inline_refs(Analysis.model_json_schema())
