"""Streamlit entrypoint. Run with: python -m streamlit run app.py."""

import streamlit as st

from c_dashboard.workspace_modes.state import ensure_registry, save_preferences
from c_dashboard.ui.mode_navigation import render_mode_navigation, render_unavailable_mode
from c_dashboard.ui.layout import render_dashboard


def main() -> None:
    st.set_page_config(
        page_title="FCCL 品質監控",
        page_icon="📊",
        layout="wide",
    )
    try:
        registry = ensure_registry(st.session_state)
    except ValueError as exc:
        st.warning(str(exc))
        st.stop()
    render_mode_navigation(registry)
    if registry.active_mode == "analysis":
        render_dashboard(registry.workspaces["analysis"])
    else:
        render_unavailable_mode(registry)
    save_preferences(registry, st.session_state)


if __name__ == "__main__":
    main()
