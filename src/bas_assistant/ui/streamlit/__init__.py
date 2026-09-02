"""Streamlit mission-control web presentation package."""

from __future__ import annotations

from bas_assistant.ui.streamlit.components import (
    annotate_pipeline_frame,
    render_event_stream_html,
    render_gates_panel_html,
    render_step_card_html,
    render_stepper_html,
    render_telemetry_bar_html,
)
from bas_assistant.ui.streamlit.tabs import (
    render_architecture_tab,
    render_live_tab,
    render_metrics_tab,
)
from bas_assistant.ui.streamlit.theme import get_streamlit_css

__all__ = [
    "annotate_pipeline_frame",
    "get_streamlit_css",
    "render_architecture_tab",
    "render_event_stream_html",
    "render_gates_panel_html",
    "render_live_tab",
    "render_metrics_tab",
    "render_step_card_html",
    "render_stepper_html",
    "render_telemetry_bar_html",
]
