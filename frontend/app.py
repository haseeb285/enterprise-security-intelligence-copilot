"""Lightweight Streamlit client for the Enterprise Security Intelligence Copilot."""

import os
from datetime import date

import streamlit as st

from frontend.client import ApiClient, ApiClientError, InvestigationResponse, MLEvidence
from frontend.support import audit_rows, count_values, event_rows, feature_rows, safe_text

DISCLAIMER = (
    "This model is trained and evaluated on synthetic demonstration data and is not a "
    "production security detection engine."
)
EXAMPLES = {
    "Policy only": "What does the password policy require for human accounts?",
    "Event investigation": "Show failed logins for U104 on 2026-08-31.",
    "ML anomaly": "What is the anomaly score for U104 on 2026-08-31?",
    "Event + policy": (
        "What does the MFA policy require, and what failed login events were recorded for U104 "
        "on 2026-08-31?"
    ),
    "Event + ML + policy": (
        "Investigate suspicious activity for U104 on 2026-08-31 and determine whether relevant "
        "password policy controls apply."
    ),
    "Impossible travel limitation": "Is U105 behaving unusually on 2026-08-31?",
    "Insufficient evidence": "What is the anomaly score for U999 on 2026-08-31?",
}


def show_error(exc: ApiClientError) -> None:
    if exc.kind in {"authentication_required", "unauthorized"}:
        st.warning(safe_text(exc))
    elif exc.kind == "forbidden":
        st.info(safe_text(exc))
    else:
        st.error(safe_text(exc))


def render_observed(items) -> None:
    st.subheader("Observed evidence")
    if not items:
        st.caption("No observed event or incident evidence was returned.")
        return
    for item in items:
        with st.expander(f"{item.kind.title()} · {item.source_id}", expanded=True):
            if item.attributes:
                st.dataframe([item.attributes], width="stretch", hide_index=True)
            st.text(safe_text(item.text))
            st.caption(f"Provenance: {safe_text(item.source)}")


def render_ml(items: list[MLEvidence]) -> None:
    st.subheader("ML analysis")
    st.caption(DISCLAIMER)
    if not items:
        st.caption("No valid ML observation was returned.")
        return
    for item in items:
        st.markdown(f"**{safe_text(item.entity_type.title())}: {safe_text(item.entity_id)}**")
        score, flag, version = st.columns(3)
        score.metric("Anomaly score", f"{item.anomaly_score:.17g}")
        flag.metric("Model flag", "Flagged" if item.flagged_anomalous else "Not flagged")
        version.metric("Model version", safe_text(item.model_version, max_chars=80))
        st.caption(
            f"Window: {item.window_start.isoformat()} to {item.window_end.isoformat()} · "
            "Score is not a probability; the flag is not proof of an attack."
        )
        st.markdown("**Contributing observations**")
        for observation in item.contributing_observations:
            st.text(f"• {safe_text(observation)}")
        rows = feature_rows(item)
        st.dataframe(rows, width="stretch", hide_index=True)
        st.bar_chart(rows, x="feature", y="value", horizontal=True)
        st.caption(
            "Provenance: "
            + " · ".join(f"{safe_text(k)}={safe_text(v)}" for k, v in item.provenance.items())
        )


def render_policy(items) -> None:
    st.subheader("Policy context")
    if not items:
        st.caption("No relevant fictional policy evidence was returned.")
        return
    for item in items:
        citation = item.citation or {}
        document = safe_text(citation.get("document", "Unknown document"))
        with st.expander(f"{document} · {item.source_id}", expanded=True):
            st.text(safe_text(item.text))
            fields = [
                f"Section: {safe_text(citation.get('section', 'n/a'))}",
                f"Source: {safe_text(citation.get('source', item.source))}",
            ]
            if citation.get("page") is not None:
                fields.append(f"Page: {citation['page']}")
            st.caption(" · ".join(fields))


def render_investigation(result: InvestigationResponse) -> None:
    st.subheader("Summary")
    st.text(safe_text(result.summary))
    render_observed(result.observed_evidence)
    render_ml(result.ml_analysis)
    render_policy(result.policy_context)
    st.subheader("AI interpretation")
    st.text(safe_text(result.interpretation))
    st.subheader("Recommended next steps")
    if result.recommended_next_steps:
        for step in result.recommended_next_steps:
            st.text(f"• {safe_text(step)}")
    else:
        st.caption("No supported recommendation was returned.")
    st.subheader("Sources")
    st.text("\n".join(safe_text(source) for source in result.sources) or "No sources")
    st.subheader("Evidence sufficiency")
    if result.evidence_sufficiency:
        st.success(f"Sufficient for the requested bounded workflow · outcome={result.outcome}")
    else:
        st.warning(f"Evidence is incomplete · outcome={result.outcome}")
    with st.expander("Safe execution metadata"):
        st.json(
            {
                "selected_tools": result.selected_tools,
                "tool_results": result.tool_results,
                "errors": result.errors,
                "graph_steps": result.graph_steps,
                "tool_calls": result.tool_calls,
            }
        )


def dashboard(client: ApiClient) -> None:
    st.title("Security overview")
    st.caption("SYNTHETIC DEMONSTRATION DATA · Read-only simulated SIEM")
    try:
        health = client.health()
        events = client.events(limit=100)
    except ApiClientError as exc:
        show_error(exc)
        return
    incident_total: int | None = None
    incidents = []
    try:
        incident_page = client.incidents(limit=5)
        incident_total, incidents = incident_page.total, incident_page.items
    except ApiClientError as exc:
        if exc.kind != "forbidden":
            show_error(exc)
    event_metric, incident_metric, health_metric = st.columns(3)
    event_metric.metric("Synthetic events", events.total)
    incident_metric.metric("Incidents", incident_total if incident_total is not None else "Admin")
    health_metric.metric("System", health.status.title())
    st.caption("Distributions use only the latest bounded sample of up to 100 events.")
    left, right = st.columns(2)
    with left:
        st.markdown("**Event types**")
        event_types = [
            {"event_type": key, "count": value}
            for key, value in count_values(events.items, "event_type").items()
        ]
        st.bar_chart(event_types, x="event_type", y="count")
    with right:
        st.markdown("**Severity**")
        severities = [
            {"severity": key, "count": value}
            for key, value in count_values(events.items, "severity").items()
        ]
        st.bar_chart(severities, x="severity", y="count")
    st.subheader("Recent events")
    st.dataframe(event_rows(events.items[:10]), width="stretch", hide_index=True)
    if incidents:
        st.subheader("Recent incidents")
        st.dataframe(
            [item.model_dump(mode="json") for item in incidents],
            width="stretch",
            hide_index=True,
        )


def investigation_copilot(client: ApiClient) -> None:
    st.title("Investigation Copilot")
    st.caption(
        "Bounded, read-only evidence analysis. Typical local completion is about 29 seconds."
    )
    choice = st.selectbox("Example investigations", list(EXAMPLES), key="example_choice")
    if st.button("Use selected example"):
        st.session_state["investigation_query"] = EXAMPLES[choice]
    query = st.text_area(
        "Investigation request",
        key="investigation_query",
        height=120,
        placeholder="Ask about synthetic events, anomaly behavior, or fictional policy controls.",
    )
    if st.button("Run investigation", type="primary", disabled=not query.strip()):
        with st.spinner(
            "FastAPI is running the bounded LangGraph workflow. This is non-streaming."
        ):
            try:
                st.session_state["investigation_result"] = client.investigate(query.strip())
            except ApiClientError as exc:
                st.session_state.pop("investigation_result", None)
                show_error(exc)
    result = st.session_state.get("investigation_result")
    if result:
        render_investigation(result)


def security_events(client: ApiClient) -> None:
    st.title("Security events")
    st.caption("Bounded reads from the synthetic simulated SIEM through FastAPI.")
    with st.form("event_filters"):
        first = st.columns(3)
        user_id = first[0].text_input("User ID", placeholder="U104")
        event_type = first[1].text_input("Event type", placeholder="failed_login")
        severity = first[2].selectbox("Severity", ["", "low", "medium", "high", "critical"])
        second = st.columns(3)
        source_ip = second[0].text_input("Source IP", placeholder="203.0.113.10")
        device_id = second[1].text_input("Device ID", placeholder="D104")
        page_size = second[2].selectbox("Page size", [10, 25, 50], index=1)
        third = st.columns(2)
        start_time = third[0].text_input("Start time", placeholder="2026-08-31T00:00:00Z")
        end_time = third[1].text_input("End time", placeholder="2026-09-01T00:00:00Z")
        submitted = st.form_submit_button("Apply filters")
    if submitted:
        st.session_state["events_offset"] = 0
    offset = st.session_state.get("events_offset", 0)
    filters = {
        "user_id": user_id.strip(),
        "event_type": event_type.strip(),
        "severity": severity,
        "source_ip": source_ip.strip(),
        "device_id": device_id.strip(),
        "start_time": start_time.strip(),
        "end_time": end_time.strip(),
    }
    try:
        page = client.events(filters, limit=page_size, offset=offset)
    except ApiClientError as exc:
        show_error(exc)
        return
    st.caption(f"Showing {len(page.items)} of {page.total} matching events · offset {page.offset}")
    st.dataframe(event_rows(page.items), width="stretch", hide_index=True)
    previous, following = st.columns(2)
    if previous.button("Previous", disabled=offset == 0):
        st.session_state["events_offset"] = max(0, offset - page_size)
        st.rerun()
    if following.button("Next", disabled=offset + page_size >= page.total):
        st.session_state["events_offset"] = offset + page_size
        st.rerun()
    if page.items:
        event_id = st.selectbox("View event details", [item.event_id for item in page.items])
        if st.button("Load event"):
            try:
                event = client.event(event_id)
                st.json(event.model_dump(mode="json"))
            except ApiClientError as exc:
                show_error(exc)


def knowledge_base(client: ApiClient) -> None:
    st.title("Knowledge base")
    st.caption("Evidence-only retrieval from the fictional policy corpus. No LLM generation.")
    with st.form("knowledge_search"):
        query = st.text_input("Policy search", placeholder="remote access MFA")
        top_k = st.slider("Maximum results", 1, 10, 5)
        submitted = st.form_submit_button("Retrieve evidence", disabled=not query.strip())
    if not submitted:
        return
    try:
        result = client.retrieve(query.strip(), top_k=top_k)
    except ApiClientError as exc:
        show_error(exc)
        return
    if result.insufficient_evidence or not result.evidence:
        st.warning("Insufficient relevant policy evidence.")
    for item in result.evidence:
        with st.expander(
            f"{safe_text(item.citation.document)} · relevance {item.score:.3f}", expanded=True
        ):
            st.text(safe_text(item.text))
            page = f" · page {item.citation.page}" if item.citation.page is not None else ""
            st.caption(
                f"Section: {safe_text(item.citation.section)} · "
                f"Source: {safe_text(item.citation.source)}{page} · chunk {item.chunk_id}"
            )


def ml_analytics(client: ApiClient) -> None:
    st.title("ML analytics")
    st.warning(DISCLAIMER)
    st.markdown(
        "Isolation Forest scores active users over one UTC day using 20 aggregate behavioral "
        "features. The score is not a probability. The model has a documented false-positive "
        "rate on synthetic holdout data and misses the U105 impossible-travel sequence because "
        "daily aggregates lose sequence semantics."
    )
    with st.form("ml_analysis"):
        user_id = st.text_input("Synthetic user", value="U105")
        analysis_date = st.date_input("UTC observation day", value=date(2026, 8, 31))
        submitted = st.form_submit_button("Run through FastAPI", disabled=not user_id.strip())
    if not submitted:
        return
    query = f"What is the anomaly score for {user_id.strip()} on {analysis_date.isoformat()}?"
    with st.spinner("Requesting typed ML evidence through the investigation API."):
        try:
            result = client.investigate(query)
        except ApiClientError as exc:
            show_error(exc)
            return
    render_ml(result.ml_analysis)
    st.subheader("Evidence status")
    st.text(safe_text(result.interpretation))
    st.caption(f"Outcome: {result.outcome}")


def system_health(client: ApiClient) -> None:
    st.title("System health")
    st.caption("Coarse readiness only; sensitive configuration is not exposed.")
    try:
        health = client.health()
    except ApiClientError as exc:
        show_error(exc)
        return
    if health.status == "ready":
        st.success("FastAPI and required local dependencies are ready.")
    else:
        st.warning("One or more local dependencies are degraded.")
    for name, state in health.dependencies.items():
        label, value = st.columns([2, 1])
        label.write(name.replace("_", " ").title())
        value.write("✅ Ready" if state == "ok" else f"⚠️ {safe_text(state)}")


def audit_about(client: ApiClient) -> None:
    st.title("Audit / About")
    st.subheader("Bounded audit metadata")
    st.caption(
        "Admin demo token required. Detail payloads, prompts, evidence, and tokens are omitted."
    )
    try:
        page = client.audit(limit=50)
        st.caption(f"Latest {len(page.items)} of {page.total} audit records")
        st.dataframe(audit_rows(page.items), width="stretch", hide_index=True)
    except ApiClientError as exc:
        show_error(exc)
    st.subheader("Architecture")
    st.code(
        "Streamlit → FastAPI → LangGraph\n"
        "                     ├─ PostgreSQL simulated SIEM\n"
        "                     ├─ Qdrant fictional policy RAG\n"
        "                     ├─ Isolation Forest anomaly model\n"
        "                     └─ native Ollama local LLM",
        language=None,
    )
    st.markdown(
        "This local-first portfolio demonstration uses synthetic telemetry, fictional policies, "
        "demo bearer authentication, application-owned provenance, and read-only tools. Streamlit "
        "is an HTTP client and never connects directly to backend data or model services."
    )


st.set_page_config(page_title="Security Intelligence Copilot", page_icon="🛡️", layout="wide")
st.sidebar.title("Security Intelligence Copilot")
st.sidebar.caption("SYNTHETIC DEMONSTRATION DATA")
base_url = st.sidebar.text_input(
    "FastAPI base URL",
    value=os.getenv("ESIC_API_BASE_URL", "http://127.0.0.1:8000/api/v1"),
)
token = st.sidebar.text_input(
    "Demo bearer token",
    type="password",
    help="Use the local reader or admin token. It is kept only in this Streamlit session.",
)
st.sidebar.caption("DEMO authentication · not enterprise SSO")
page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Investigation Copilot",
        "Security Events",
        "Knowledge Base",
        "ML Analytics",
        "System Health",
        "Audit / About",
    ],
)

try:
    api = ApiClient(base_url, token)
except ValueError as exc:
    st.error(safe_text(exc))
    st.stop()

pages = {
    "Dashboard": dashboard,
    "Investigation Copilot": investigation_copilot,
    "Security Events": security_events,
    "Knowledge Base": knowledge_base,
    "ML Analytics": ml_analytics,
    "System Health": system_health,
    "Audit / About": audit_about,
}
pages[page](api)
