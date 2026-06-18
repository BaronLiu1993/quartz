from unittest.mock import Mock, patch

from agents.orchestrator_agent import OrchestratorState, decide_pr_workflow, _load_system_orchestrator_prompt, build_workflow_steps, plan_pr_workflow


def test_decide_pr_workflow_returns_structured_llm_decision() -> None:
    expected_decision = OrchestratorState(
        review_agent_needed=True,
        execution_agent_needed=True,
        codebase_context_needed=True,
        reason="PR changes HDL files.",
    )

    pr_context = {
        "repo_full_name": "octo/demo",
        "pr_number": 7,
        "metadata": {
            "title": "Add counter",
            "files_changed": ["rtl/counter.sv"],
        },
    }

    fake_orchestrator = Mock()
    fake_orchestrator.invoke.return_value = expected_decision

    with patch("agents.orchestrator_agent.get_orchestrator", return_value=fake_orchestrator):
        result = decide_pr_workflow(pr_context)

    assert result == expected_decision
    fake_orchestrator.invoke.assert_called_once()

def test_load_system_orchestrator_prompt() -> None:
    prompt = _load_system_orchestrator_prompt()

    assert "orchestrator agent" in prompt
    assert "execution_agent_needed" in prompt
    assert "review_agent_needed" in prompt

def test_build_workflow_steps_orders_context_execution_review() -> None:
    decision = OrchestratorState(
        review_agent_needed=True,
        execution_agent_needed=True,
        codebase_context_needed=True,
        reason="Needs everything.",
    )

    result = build_workflow_steps(decision)

    assert result == ["codebase_context", "execution", "review"]

def test_build_workflow_steps_only_includes_needed_steps() -> None:
    decision = OrchestratorState(
        review_agent_needed=True,
        execution_agent_needed=False,
        codebase_context_needed=False,
        reason="Only review is needed.",
    )

    result = build_workflow_steps(decision)

    assert result == ["review"]

def test_plan_pr_workflow_returns_decision_and_steps() -> None:
    decision = OrchestratorState(
        review_agent_needed=True,
        execution_agent_needed=True,
        codebase_context_needed=False,
        reason="HDL changed.",
    )

    pr_context = {
        "repo_full_name": "octo/demo",
        "pr_number": 7,
    }

    with patch("agents.orchestrator_agent.decide_pr_workflow", return_value=decision) as fake_decide:
        result = plan_pr_workflow(pr_context)

    assert result == {
        "decision": decision,
        "steps": ["execution", "review"],
    }

    fake_decide.assert_called_once_with(pr_context)
