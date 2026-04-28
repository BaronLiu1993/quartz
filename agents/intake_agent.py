from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional
from langchain_openai import ChatOpenAI
from langchain.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.types import interrupt, Command
from pymongo import MongoClient

from memory import insert_raw_conversation_memory, RawConveresationModel
from pathlib import Path
import json
import operator


MAX_TURNS = 5
MODEL_NAME = "gpt-5.4"
MAX_TOKENS = 2000
MONGO_URI = "mongodb://localhost:27017"
CHECKPOINT_DB = "checkpoints"
_PROMPT_PATH = Path(__file__).resolve().parent.parent / "skills" / "intent-agent-001.MD"


def _load_system_prompt() -> str:
    """Load the intent-agent system prompt from the skills directory."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


INTAKE_SYSTEM_PROMPT: str = _load_system_prompt()

class IntakeInputModel(BaseModel):
    user_id: str
    session_id: str
    prompt: str
    code: str


class Option(BaseModel):
    option_id: str
    description: str


class Question(BaseModel):
    question_id: str
    question: str
    options: list[Option] = Field(..., min_length=1)


class Answer(BaseModel):
    question_id: str
    option_id: Optional[str] = None
    free_text: Optional[str] = None


class OrchestratorOutputModel(BaseModel):
    context: str
    clarification_questions: list[Question] = Field(default_factory=list)


class EvaluationModel(BaseModel):
    enough_context: bool
    reason: str


class IntakeStateModel(BaseModel):
    input: IntakeInputModel
    context: str = ""
    clarification_questions: list[Question] = Field(default_factory=list)
    answered_questions: Annotated[list, operator.add] = Field(default_factory=list)
    enough_context: bool = False
    turn: int = 0


class IntakeRunResult(BaseModel):
    status: Literal["pending_questions", "complete"]
    session_id: str
    questions: list[Question] = Field(default_factory=list)
    state: Optional[dict] = None

_checkpoint_client: Optional[MongoClient] = None
_compiled_graph = None

def _orchestrator_llm():
    return ChatOpenAI(
        model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=0.2
    ).with_structured_output(OrchestratorOutputModel)


def _evaluator_llm():
    return ChatOpenAI(
        model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=0.2
    ).with_structured_output(EvaluationModel)


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


def _record_answers(input_: IntakeInputModel, answers: list) -> None:
    serialised = [a if isinstance(a, dict) else a.model_dump() for a in answers]
    insert_raw_conversation_memory(
        [
            RawConveresationModel(
                user_id=input_.user_id,
                session_id=input_.session_id,
                stage="intake",
                type="user_response",
                raw_conversation=json.dumps(serialised),
            )
        ]
    )


def orchestrator_node(state: IntakeStateModel) -> dict:
    if state.turn == 0:
        _record_intake_inputs(state.input)

    answered = [
        a if isinstance(a, dict) else a.model_dump() for a in state.answered_questions
    ]
    user_msg = (
        f"User prompt: {state.input.prompt}\n\n"
        f"Code:\n{state.input.code}\n\n"
        f"Context so far: {state.context or '(none)'}\n\n"
        f"Answered questions so far: {answered or '(none)'}\n\n"
        "Update the context summary with what is now understood, and emit any "
        "clarification_questions you still need answered. If nothing remains "
        "ambiguous, return an empty clarification_questions list."
    )
    result: OrchestratorOutputModel = _orchestrator_llm().invoke(
        [SystemMessage(content=INTAKE_SYSTEM_PROMPT), HumanMessage(content=user_msg)]
    )
    return {
        "context": result.context,
        "clarification_questions": result.clarification_questions,
        "turn": state.turn + 1,
    }


def human_node(state: IntakeStateModel) -> dict:
    if not state.clarification_questions:
        return {}
    payload = {"questions": [q.model_dump() for q in state.clarification_questions]}
    answers = interrupt(payload)
    _record_answers(state.input, answers)
    return {"answered_questions": answers, "clarification_questions": []}


def evaluation_node(state: IntakeStateModel) -> dict:
    answered = [
        a if isinstance(a, dict) else a.model_dump() for a in state.answered_questions
    ]
    user_msg = (
        f"Context: {state.context or '(none)'}\n\n"
        f"Answered questions: {answered or '(none)'}\n\n"
        "Decide if there is enough context to proceed to test design. Set "
        "enough_context=true only when no blocking ambiguity remains."
    )
    result: EvaluationModel = _evaluator_llm().invoke(
        [
            SystemMessage(
                content=(
                    "You are the readiness evaluator for the intake agent. "
                    "Output enough_context=true only when the context is "
                    "sufficient to design meaningful tests."
                )
            ),
            HumanMessage(content=user_msg),
        ]
    )
    return {"enough_context": result.enough_context}


def route_after_eval(state: IntakeStateModel) -> str:
    if state.enough_context or state.turn >= MAX_TURNS:
        return END
    return "orchestrator"


def _get_checkpointer() -> MongoDBSaver:
    global _checkpoint_client
    if _checkpoint_client is None:
        _checkpoint_client = MongoClient(MONGO_URI)
    return MongoDBSaver(_checkpoint_client, db_name=CHECKPOINT_DB)


def _get_graph():
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph
    g = StateGraph(IntakeStateModel)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("human", human_node)
    g.add_node("evaluator", evaluation_node)
    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "human")
    g.add_edge("human", "evaluator")
    g.add_conditional_edges(
        "evaluator",
        route_after_eval,
        {"orchestrator": "orchestrator", END: END},
    )
    _compiled_graph = g.compile(checkpointer=_get_checkpointer())
    return _compiled_graph


def _to_run_result(result: dict, session_id: str) -> IntakeRunResult:
    interrupts = result.get("__interrupt__")
    if interrupts:
        payload = interrupts[0].value
        return IntakeRunResult(
            status="pending_questions",
            session_id=session_id,
            questions=[Question(**q) for q in payload["questions"]],
        )
    return IntakeRunResult(status="complete", session_id=session_id, state=result)


def start_intake(request: IntakeInputModel) -> IntakeRunResult:
    """Begin a new intake session. Returns either pending questions or final state."""
    graph = _get_graph()
    config = {"configurable": {"thread_id": request.session_id}}
    result = graph.invoke(IntakeStateModel(input=request).model_dump(), config=config)
    return _to_run_result(result, request.session_id)


def resume_intake(session_id: str, answers: list[Answer]) -> IntakeRunResult:
    """Resume a paused intake session by supplying human answers."""
    graph = _get_graph()
    config = {"configurable": {"thread_id": session_id}}
    payload = [a.model_dump() for a in answers]
    result = graph.invoke(Command(resume=payload), config=config)
    return _to_run_result(result, session_id)
