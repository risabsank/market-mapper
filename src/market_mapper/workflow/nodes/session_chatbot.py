"""Session chatbot workflow node."""

from __future__ import annotations

from market_mapper.agents.session_chatbot import run_session_chatbot
from market_mapper.services.session_service import SessionStateService
from market_mapper.workflow.contracts import SessionChatbotNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def session_chatbot_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Mark the session chatbot as ready after dashboard generation."""

    snapshot = SessionStateService().save_approved_snapshot(
        session=state.session,
        run=state.run,
        dashboard_state=state.dashboard_state,
        company_profiles=state.company_profiles,
        comparison_result=state.comparison_result,
        report=state.report,
        chart_specs=state.chart_specs,
        source_documents=state.source_documents,
    )
    state.session.metadata["approved_session_snapshot_id"] = snapshot.id
    state.touch()
    task = start_agent_task(
        state,
        agent_name="session_chatbot",
        task_type="prepare_session_chat",
        inputs={"dashboard_state_id": state.dashboard_state.id},
    )
    node_output = run_session_chatbot(
        SessionChatbotNodeInput(
            session_id=state.session.id,
            run_id=state.run.id,
            dashboard_state=state.dashboard_state,
        )
    )
    state.run.mark_completed(current_node="session_chatbot")
    state.session.status = state.run.status
    complete_agent_task(
        state,
        task=task,
        outputs={
            "chat_ready": node_output.chat_ready,
            "approved_session_snapshot_id": snapshot.id,
        },
        summary=node_output.summary,
    )
    return state
