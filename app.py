"""
app.py
------
Entry point for CORRECTabel.

This file does three things only:
  1. Configures the Streamlit page (title, layout)
  2. Injects the CSS from styles/main.css
  3. Reads the URL param ?p= to decide which page to show,
     renders the navbar, then calls the right page module

All actual logic lives in pages/ and utils/.
Run with:  streamlit run app.py
"""

import subprocess
import sys

# Auto-install reportlab if missing (needed for PDF support)
try:
    import reportlab
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "--quiet"])

import os
import streamlit as st

# ── Page imports ──────────────────────────────────────────────────────────────
from pages.about import render as render_about
from pages.clean import render as render_clean
from pages.labelstudio import render as render_labelstudio
from pages.review import render as render_review

# ── Streamlit config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CORRECTabel",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inject CSS ────────────────────────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(__file__), "styles", "main.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
_defaults = {
    "push_running": False,  "push_aborted": False,   "push_done": False,
    "push_log": [],         "push_progress": 0.0,    "push_status": "",
    "push_queue": [],       "push_queue_idx": 0,     "push_total_uploaded": 0,
    "review_running": False,"review_aborted": False,  "review_done": False,
    "review_progress": 0.0,"review_status": "",
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Routing — reads ?p= from the URL ─────────────────────────────────────────
qp = st.query_params
VALID_PAGES = ("about", "clean", "labelstudio", "review")

if "p" in qp and qp["p"] in VALID_PAGES:
    st.session_state.page = qp["p"]
elif "page" not in st.session_state:
    st.session_state.page = "about"

page = st.session_state.page


def nav_link(label: str, target: str, current: str) -> str:
    """Returns an HTML <a> tag styled as active or inactive."""
    active_class = "nav-link active" if current == target else "nav-link"
    return f'<a class="{active_class}" href="?p={target}" target="_self">{label}</a>'


# ── Navbar ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="navbar">
    <div class="nav-logo">CORRECT<span>abel</span></div>
    <div class="nav-links">
        {nav_link("Home",          "about",        page)}
        {nav_link("Clean",         "clean",        page)}
        {nav_link("Label Studio",  "labelstudio",  page)}
        {nav_link("Review",        "review",       page)}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Page dispatch ─────────────────────────────────────────────────────────────
if page == "about":
    render_about()
elif page == "clean":
    render_clean()
elif page == "labelstudio":
    render_labelstudio()
elif page == "review":
    render_review()
