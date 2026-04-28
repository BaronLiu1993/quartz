from pydantic import BaseModel, Field
from typing import Literal
from config import get_openai_client
from memory import insert_raw_conversation_memory, RawConveresationModel
from pathlib import Path

MAX_TURNS = 5
MODEL_NAME = "gpt-5.4"
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "skills" / "intent-agent-001.MD"


def _load_system_prompt() -> str:
    """Load the intent-agent system prompt from the skills directory."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


INTAKE_SYSTEM_PROMPT: str = _load_system_prompt()


# Clarifies User Intent
class IntakeInputModel(BaseModel):
    user_id: str
    session_id: str
    prompt: str
    code: str

class GroundedClaimModel(BaseModel):
    statement: str
    grounded_in: Literal["code", "query", "user_confirmation"]
    evidence: str


class IntakeOutputModel(BaseModel):
    finished: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    answered_questions: list[str] = Field(default_factory=list)
    context: str
    finalised_context: str = ""


def _record_intake_inputs(request: IntakeInputModel) -> None:
    insert_raw_conversation_memory(
        [
            RawConveresationModel(
                user_id=request.user_id,
                session_id=request.session_id,
                stage="intake",
                type="code",
                raw_conversation=request.code,
            ),
            RawConveresationModel(
                user_id=request.user_id,
                session_id=request.session_id,
                stage="intake",
                type="prompt",
                raw_conversation=request.prompt,
            ),
        ]
    )


async def intake_node(request: IntakeInputModel) -> IntakeOutputModel:
    finished = False
    messages = [
        [
            {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
            {"role": "user", "content": ""},
        ]
    ]
    client = get_openai_client()
    _record_intake_inputs(request)
    while not finished:
        completion = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            response_format=IntakeOutputModel,
        )
        response_content = completion.choices[0].message.content
        messages.append({"role": "assistant", "content": response_content.context})
        finished = response_content.finished
    return response_content


def main():
    pass
