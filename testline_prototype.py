"""Gate 0 static Streamlit prototype.

Run with: python -m streamlit run testline_prototype.py
"""

import importlib

import streamlit as st

import c_dashboard.testline_prototype as prototype


def main() -> None:
    st.set_page_config(
        page_title="FCCL 測試線模擬控制台｜靜態原型",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    # Streamlit reruns entry files but may retain imported project modules.
    # Reload the Gate 0 UI so local fixes cannot leave stale callbacks behind.
    importlib.reload(prototype)
    prototype.render_testline_prototype()


if __name__ == "__main__":
    main()
