"""Synthetic v3 test-line control-room entrypoint."""

import streamlit as st

from c_dashboard.testline_control_room import render_testline_control_room


def main() -> None:
    st.set_page_config(
        page_title="FCCL 測試線模擬控制台",
        page_icon="🏭",
        layout="wide",
    )
    render_testline_control_room()


if __name__ == "__main__":
    main()
