"""Tab layouts and execution handlers for the Streamlit dashboard."""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import av
import cv2
from streamlit_webrtc import WebRtcMode, webrtc_streamer

import streamlit as st
from bas_assistant.ui.state import build_status_snapshot
from bas_assistant.ui.streamlit.components import (
    annotate_pipeline_frame,
    render_event_stream_html,
    render_gates_panel_html,
    render_step_card_html,
    render_stepper_html,
    render_telemetry_bar_html,
)
from bas_assistant.ui.theme import EVENT_TYPE_COLORS, TEXT_MUTED
from bas_assistant.validation.protocol import DEFAULT_MICROPHONE_PROTOCOL


def process_video_loop(
    pipeline: Any,
    video_path: str | Path,
    frame_slot: Any,
    is_stopped_fn: Callable[[], bool],
    update_cb: Callable[[dict[str, Any]], None],
    event_history: list[str],
) -> None:
    """Read and evaluate frames from a video stream."""
    cap = cv2.VideoCapture(str(video_path))
    pipeline.start_session()

    try:
        while cap.isOpened():
            if is_stopped_fn():
                break
            ret, frame = cap.read()
            if not ret:
                break

            res = pipeline.process_frame(frame)
            snap = build_status_snapshot(pipeline, res, DEFAULT_MICROPHONE_PROTOCOL)

            annotated = annotate_pipeline_frame(frame, res)
            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            frame_slot.image(frame_rgb, channels="RGB", use_container_width=True)

            if res.new_events:
                for ev in res.new_events:
                    color_tag, badge, _ = EVENT_TYPE_COLORS.get(ev.type, ("#94A3B8", "INFO", ""))
                    event_history.append(
                        f"<span style='color: {color_tag}; font-weight: bold;'>[{badge}]</span> "
                        f"<b>{ev.step or ''}</b> {ev.message} "
                        f"<span style='color: {TEXT_MUTED};'>({ev.timestamp:.1f}s)</span>"
                    )

            update_cb(snap)
    finally:
        cap.release()
        pipeline.end_session()


def render_live_tab(pipeline: Any, input_mode: str, event_history: list[str]) -> None:
    """Render the primary live video & telemetry monitoring view."""
    telemetry_slot = st.empty()

    initial_snap = {
        "status": "READY",
        "fps": 0.0,
        "latency_ms": 0.0,
        "step_id": None,
        "step": "Idle / Standby",
        "confidence": 0.0,
        "gate_status": "not_required",
        "done_steps": [],
        "expected_next_id": "M0",
        "led": {"left": "off", "right": "off"},
    }

    col_video, col_telemetry = st.columns([1.7, 1.3])

    with col_telemetry:
        step_slot = st.empty()
        gates_slot = st.empty()
        stepper_slot = st.empty()
        st.markdown(
            "<div class='mc-card-header'>Activity Log & Sequence Alerts</div>",
            unsafe_allow_html=True,
        )
        log_slot = st.empty()

    def update_views(snap: dict[str, Any]) -> None:
        telemetry_slot.markdown(render_telemetry_bar_html(snap), unsafe_allow_html=True)
        step_slot.markdown(render_step_card_html(snap), unsafe_allow_html=True)
        gates_slot.markdown(render_gates_panel_html(snap), unsafe_allow_html=True)
        stepper_slot.markdown(
            render_stepper_html(snap["done_steps"], snap["expected_next_id"]),
            unsafe_allow_html=True,
        )
        log_slot.markdown(render_event_stream_html(event_history), unsafe_allow_html=True)

    update_views(initial_snap)

    _render_intake_mode(input_mode, pipeline, col_video, event_history, update_views)


def _render_intake_mode(
    input_mode: str,
    pipeline: Any,
    col_video: Any,
    event_history: list[str],
    update_cb: Callable[[dict[str, Any]], None],
) -> None:
    """Handle specific video source layout and execution."""
    if input_mode == "Demo Video (data/raw)":
        _render_demo_video_mode(pipeline, col_video, event_history, update_cb)
    elif input_mode == "Upload Video File":
        _render_upload_mode(pipeline, col_video, event_history, update_cb)
    elif input_mode == "Browser Webcam (WebRTC)":
        _render_webrtc_mode(pipeline, col_video)
    else:
        _render_dummy_mode(pipeline, col_video, update_cb)


def _render_demo_video_mode(
    pipeline: Any, col_video: Any, event_history: list[str], update_cb: Callable
) -> None:
    with col_video:
        st.markdown(
            "<div class='mc-card-header'>Video Viewport (data/raw)</div>",
            unsafe_allow_html=True,
        )
        raw_dir = Path("data/raw")
        v_exts = ("*.mp4", "*.avi", "*.mov")
        files = [p for ext in v_exts for p in raw_dir.glob(ext)]
        names = [f.name for f in files]

        if not files:
            st.warning("No video files found in data/raw/.")
            return

        c_sel, c_ctrl = st.columns([1.5, 1])
        selected_name = c_sel.selectbox("Select Experiment Video", names, index=0)
        c1, c2 = c_ctrl.columns(2)
        start_btn = c1.button("▶️ START", type="primary")
        stop_btn = c2.checkbox("⏹️ STOP", value=False)
        frame_slot = st.empty()

        if start_btn:
            selected_path = raw_dir / selected_name
            process_video_loop(
                pipeline, selected_path, frame_slot, lambda: stop_btn, update_cb, event_history
            )


def _render_upload_mode(
    pipeline: Any, col_video: Any, event_history: list[str], update_cb: Callable
) -> None:
    with col_video:
        st.markdown(
            "<div class='mc-card-header'>Video Viewport (Upload)</div>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("Upload video", type=["mp4", "avi", "mov"])
        if uploaded is not None:
            with tempfile.NamedTemporaryFile(delete=False) as tfile:
                tfile.write(uploaded.read())
                temp_name = tfile.name

            c1, c2 = st.columns(2)
            start_btn = c1.button("▶️ START", type="primary")
            stop_btn = c2.checkbox("⏹️ STOP", value=False)
            frame_slot = st.empty()

            if start_btn:
                process_video_loop(
                    pipeline, temp_name, frame_slot, lambda: stop_btn, update_cb, event_history
                )


def _render_webrtc_mode(pipeline: Any, col_video: Any) -> None:
    with col_video:
        st.markdown("<div class='mc-card-header'>Live Webcam Stream</div>", unsafe_allow_html=True)

        class WebRtcTransformer:
            def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                img = frame.to_ndarray(format="bgr24")
                res = pipeline.process_frame(img)
                annotated = annotate_pipeline_frame(img, res)
                return av.VideoFrame.from_ndarray(annotated, format="bgr24")

        webrtc_streamer(
            key="bas-streamer",
            mode=WebRtcMode.SENDRECV,
            video_frame_callback=WebRtcTransformer().recv,
            media_stream_constraints={"video": True, "audio": False},
            async_processing=True,
        )


def _render_dummy_mode(pipeline: Any, col_video: Any, update_cb: Callable) -> None:
    with col_video:
        st.markdown("<div class='mc-card-header'>Simulated Feed</div>", unsafe_allow_html=True)
        from bas_assistant.video.source import DummyVideoSource

        if st.button("▶️ Run 100-Frame Simulation", type="primary"):
            source = DummyVideoSource(num_frames=100)
            source.start()
            frame_slot = st.empty()
            pipeline.start_session()

            for _ in range(100):
                frame = source.read()
                if frame is None:
                    break
                res = pipeline.process_frame(frame)
                snap = build_status_snapshot(pipeline, res, DEFAULT_MICROPHONE_PROTOCOL)
                annotated = annotate_pipeline_frame(frame, res)
                frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                frame_slot.image(frame_rgb, channels="RGB", use_container_width=True)
                update_cb(snap)

            pipeline.end_session()


def render_metrics_tab() -> None:
    """Render the model training and evaluation curves tab."""
    st.markdown(
        "<div class='mc-card-header'>Model Training, Loss Curves & Evaluation Graphs</div>",
        unsafe_allow_html=True,
    )
    runs_base = Path("runs/detect")
    candidate_dirs = [
        runs_base / "runs" / "microphone_yolo" / "baseline-2",
        runs_base / "val",
        runs_base / "val-2",
        runs_base / "val-3",
        runs_base / "val-4",
    ]
    available_dirs = [d for d in candidate_dirs if d.exists()]

    if not available_dirs:
        st.info("No training runs found in runs/detect/.")
        return

    def fmt_dir(p: Path) -> str:
        parent = runs_base.parent
        return str(p.relative_to(parent) if parent in p.parents else p)

    selected_run = st.selectbox(
        "Select Evaluation Checkpoint / Run",
        available_dirs,
        format_func=fmt_dir,
    )
    st.markdown("---")
    _render_metric_images(selected_run)


def _render_metric_images(selected_run: Path) -> None:
    res_img = selected_run / "results.png"
    if res_img.exists():
        st.subheader("1. Training & Validation Metric Curves over Epochs")
        st.image(str(res_img), caption="YOLO Training Metrics", use_container_width=True)

    cm_raw = selected_run / "confusion_matrix.png"
    cm_norm = selected_run / "confusion_matrix_normalized.png"
    if cm_raw.exists() or cm_norm.exists():
        st.subheader("2. Multi-Class Confusion Matrices")
        c1, c2 = st.columns(2)
        if cm_raw.exists():
            c1.image(str(cm_raw), caption="Raw Confusion Matrix", use_container_width=True)
        if cm_norm.exists():
            c2.image(str(cm_norm), caption="Normalized Confusion Matrix", use_container_width=True)

    pr_img = selected_run / "BoxPR_curve.png"
    f1_img = selected_run / "BoxF1_curve.png"
    if pr_img.exists() or f1_img.exists():
        st.subheader("3. Detection Curves")
        c1, c2 = st.columns(2)
        if pr_img.exists():
            c1.image(str(pr_img), caption="Box PR Curve", use_container_width=True)
        if f1_img.exists():
            c2.image(str(f1_img), caption="Box F1 Curve", use_container_width=True)


def render_architecture_tab() -> None:
    """Render the FSM and pipeline architecture diagrams tab."""
    st.markdown(
        "<div class='mc-card-header'>Finite State Machine (FSM) & Architecture Dataflow</div>",
        unsafe_allow_html=True,
    )
    st.subheader("1. Protocol Sequence State Machine (FSM)")
    fsm_mermaid = """
    graph LR
        START([🚀 Session Start]) --> M0["M0: Verify Phone On"]
        M0 -->|confirmed| M1["M1: Move Phone"]
        M1 -->|confirmed| M2["M2: Pick Mic Case"]
        M2 -->|confirmed| M3["M3: Open Mic Case"]
        M3 -->|confirmed| M4["M4: Remove Receiver"]
        M4 -->|confirmed| M5["M5: Connect Receiver"]
        M5 -->|G1 Verified| G1{"Gate G1: Receiver Connected"}
        G1 -->|Gate Passed| M6["M6: Remove Microphone"]
        M6 -->|G2 Verified| G2{"Gate G2: Mic Paired"}
        G2 -->|Protocol Complete| END([✅ Experiment Complete])
        M2 -.->|Repeat / Skip| ERR([⚠️ Alert Event / Log])
        M4 -.->|Out of Sequence| ERR
        style G1 fill:#ff9900,stroke:#333,stroke-width:2px,color:#000
        style G2 fill:#ff9900,stroke:#333,stroke-width:2px,color:#000
        style END fill:#28a745,stroke:#333,stroke-width:2px,color:#fff
    """
    st.markdown(f"```mermaid\n{fsm_mermaid}\n```")

    st.markdown("---")
    st.subheader("2. End-to-End Pipeline Dataflow DAG")
    pipeline_mermaid = """
    graph TD
        A[📹 Video Source] --> B[Frame Intake & Normalization]
        B --> C[MediaPipe Hands: 21 Landmarks / Hand]
        B --> D[YOLO Detection: Payload Objects]
        C --> E[Feature Fusion Vector]
        D --> E
        E --> F[XGBoost Step Classifier]
        F --> G[Deterministic Protocol FSM]
        G --> H[Verification Gates G1/G2]
        G --> I[Mission Control Dashboard]
        G --> J[JSONL Session Storage]
        style A fill:#4a90e2,stroke:#333,stroke-width:2px,color:#fff
        style F fill:#9013fe,stroke:#333,stroke-width:2px,color:#fff
        style G fill:#f5a623,stroke:#333,stroke-width:2px,color:#000
    """
    st.markdown(f"```mermaid\n{pipeline_mermaid}\n```")


__all__ = [
    "process_video_loop",
    "render_architecture_tab",
    "render_live_tab",
    "render_metrics_tab",
]
