"""
pages/review.py
---------------
The "Review" page.

Flow:
  1. Connect to Label Studio
  2. Configure email settings (for the report)
  3. Set review parameters (expected labels, min bbox area)
  4. Run review — fetches all projects + audits each task
  5. Display per-labeler cards with issue breakdown
  6. Send HTML report by email
"""

import streamlit as st

from utils.ls_api import ls_test_connection, ls_get_projects, analyze_project
from utils.email_utils import send_email_report, build_html_report


def render():
    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    # ── Label Studio Connection ──────────────────────────────────────────────
    st.markdown('<div class="section-label">Label Studio Connection</div>', unsafe_allow_html=True)
    st.markdown('<div class="ls-config-box">', unsafe_allow_html=True)

    rv_col1, rv_col2, rv_col3 = st.columns([2, 2, 1])
    with rv_col1:
        rv_url = st.text_input(
            "Label Studio URL",
            value=st.session_state.get("ls_url", "http://localhost:8080"),
            key="rv_url_input",
        )
    with rv_col2:
        rv_api = st.text_input(
            "API Key",
            value=st.session_state.get("ls_api_key", ""),
            type="password",
            key="rv_api_input",
        )
    with rv_col3:
        st.write("")
        st.write("")
        if st.button("Connect", key="btn_rv_connect"):
            ok, resp = ls_test_connection(rv_url, rv_api)
            if ok:
                st.session_state.ls_url = rv_url
                st.session_state.ls_api_key = rv_api
                st.session_state.ls_connected = True
                st.success("Connected.")
            else:
                st.session_state.ls_connected = False
                st.error(f"Failed — {resp}")

    if st.session_state.get("ls_connected"):
        st.markdown(
            f'<div class="ls-connected"><span class="ls-dot"></span> Connected — {st.session_state.get("ls_url","")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Email Report Settings ────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">Email Report Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="email-config-box">', unsafe_allow_html=True)

    em_col1, em_col2, em_col3 = st.columns(3)
    with em_col1:
        gmail_user = st.text_input(
            "Your Gmail Address",
            value=st.session_state.get("gmail_user", ""),
            placeholder="you@gmail.com",
            key="gmail_user_input",
        )
    with em_col2:
        gmail_pass = st.text_input(
            "Gmail App Password",
            value=st.session_state.get("gmail_pass", ""),
            type="password",
            placeholder="xxxx xxxx xxxx xxxx",
            key="gmail_pass_input",
        )
    with em_col3:
        to_email = st.text_input(
            "Send Report To",
            value=st.session_state.get("to_email", ""),
            placeholder="recipient@email.com",
            key="to_email_input",
        )

    if gmail_user: st.session_state.gmail_user = gmail_user
    if gmail_pass: st.session_state.gmail_pass = gmail_pass
    if to_email:   st.session_state.to_email   = to_email

    with st.expander("How to get a Gmail App Password"):
        st.markdown("""
1. Go to Google Account → **Security**
2. Enable **2-Step Verification**
3. Search **App Passwords**
4. Select Mail → Windows Computer
5. Copy the 16-character password
        """)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Review Settings ──────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">Review Settings</div>', unsafe_allow_html=True)
    st.write("")

    settings_col1, settings_col2 = st.columns([1, 1])
    with settings_col1:
        expected_labels_raw = st.text_input(
            "Expected label classes (comma separated)",
            value=st.session_state.get("expected_labels_raw", ""),
            placeholder="e.g. Car, Person, Bike",
            key="expected_labels_input",
        )
        st.session_state.expected_labels_raw = expected_labels_raw
        expected_labels = (
            [l.strip() for l in expected_labels_raw.split(",") if l.strip()]
            if expected_labels_raw.strip() else None
        )

    with settings_col2:
        st.markdown('<div style="font-size:0.72rem;color:var(--text2);margin-bottom:4px;font-family:Inter,sans-serif;">Min BBox Area % — boxes smaller than this are flagged</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.65rem;color:var(--purple);margin-bottom:8px;font-family:Inter,sans-serif;">Accidental clicks ≈ 0.1% · Small objects ≈ 1–3% · Recommended: 1.0%</div>', unsafe_allow_html=True)
        bbox_min_area = st.slider(
            "bbox_min_area",
            min_value=0.1, max_value=5.0,
            value=float(st.session_state.get("bbox_min_area", 1.0)),
            step=0.1,
            key="bbox_min_area_slider",
            label_visibility="collapsed",
        )
        st.session_state.bbox_min_area = bbox_min_area

    # ── Run Review ───────────────────────────────────────────────────────────
    st.write("")
    if st.button("Run Review", key="btn_run_review", disabled=st.session_state.get("review_running", False)):
        if not st.session_state.get("ls_connected"):
            st.error("Connect to Label Studio first.")
        else:
            st.session_state.review_running = True
            st.session_state.review_done = False
            st.session_state.review_summaries = []
            st.session_state._review_params = {
                "ls_url": st.session_state["ls_url"],
                "ls_api": st.session_state["ls_api_key"],
                "expected_labels": expected_labels,
                "bbox_min_area": bbox_min_area,
            }
            st.rerun()

    if st.session_state.get("review_running"):
        p = st.session_state._review_params
        prog_bar = st.progress(0.0)
        status_placeholder = st.empty()

        col_abort, _ = st.columns([1, 4])
        with col_abort:
            if st.button("Abort Review", key="btn_abort_review"):
                st.session_state.review_running = False
                st.rerun()

        projects, err = ls_get_projects(p["ls_url"], p["ls_api"])
        if err or not projects:
            st.error(f"Error: {err or 'No projects found'}")
            st.session_state.review_running = False
            st.rerun()
        else:
            project_summaries = []
            total_tasks_all = total_issues_all = 0

            for idx, project in enumerate(projects):
                pname = project.get("title", f"Project {project['id']}")
                status_placeholder.markdown(
                    f'<div style="font-size:0.75rem;color:var(--purple);font-family:Inter,sans-serif;">Analyzing: {pname}</div>',
                    unsafe_allow_html=True,
                )
                prog_bar.progress((idx + 1) / len(projects))

                data, err = analyze_project(
                    p["ls_url"], p["ls_api"], project,
                    p["expected_labels"], bbox_min_area=p["bbox_min_area"]
                )
                if err or data is None:
                    continue

                issues = (
                    data["unlabeled_count"]
                    + len(data["empty_annotation"])
                    + len(data["suspicious_bbox"])
                    + len(data["wrong_label"])
                )
                total_tasks_all  += data["total"]
                total_issues_all += issues
                project_summaries.append({
                    "name": pname,
                    "project_id": project["id"],
                    "data": data,
                    "issues": issues,
                })

            st.session_state.review_summaries = project_summaries
            st.session_state.review_meta = {
                "total_projects": len(project_summaries),
                "total_tasks":    total_tasks_all,
                "total_issues":   total_issues_all,
            }
            st.session_state.review_running = False
            st.session_state.review_done = True
            st.rerun()

    # ── Results Display ──────────────────────────────────────────────────────
    if not st.session_state.get("review_summaries"):
        st.markdown('</div>', unsafe_allow_html=True)
        return

    project_summaries = st.session_state.review_summaries
    meta = st.session_state.review_meta

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-box"><div class="metric-number">{meta["total_projects"]}</div><div class="metric-label">Projects</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-box"><div class="metric-number">{meta["total_tasks"]}</div><div class="metric-label">Total Images</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-box"><div class="metric-number" style="color:var(--red);">{meta["total_issues"]}</div><div class="metric-label">Total Issues</div></div>', unsafe_allow_html=True)
    with m4:
        clean_projects = sum(1 for ps in project_summaries if ps["issues"] == 0)
        st.markdown(f'<div class="metric-box"><div class="metric-number" style="color:var(--green);">{clean_projects}</div><div class="metric-label">Clean Projects</div></div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="section-label">Per-Labeler Results</div>', unsafe_allow_html=True)
    st.write("")

    for ps in project_summaries:
        d = ps["data"]
        pct      = d["completion_pct"]
        issues   = ps["issues"]
        missing_n = d["unlabeled_count"]
        empty_n   = len(d["empty_annotation"])
        bbox_n    = len(d["suspicious_bbox"])
        wrong_n   = len(d["wrong_label"])

        st.markdown(f"""<div class="review-card">
            <div class="review-card-header">
                <div>
                    <div class="review-labeler-name">{ps['name']}</div>
                    <div class="review-project-id">Project ID: {ps['project_id']}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:Manrope,sans-serif;font-size:1.8rem;font-weight:800;color:{'var(--red)' if issues>0 else 'var(--green)'};">{issues}</div>
                    <div style="font-size:0.62rem;color:var(--text2);letter-spacing:2px;text-transform:uppercase;font-family:Cabin,sans-serif;">Total Issues</div>
                </div>
            </div>
            <div class="review-stats">
                <div class="review-stat"><div class="review-stat-num">{d['total']}</div><div class="review-stat-label">Total</div></div>
                <div class="review-stat"><div class="review-stat-num green">{d['labeled']}</div><div class="review-stat-label">Labeled</div></div>
                <div class="review-stat"><div class="review-stat-num {'red' if missing_n>0 else 'green'}">{missing_n}</div><div class="review-stat-label">Missing</div></div>
                <div class="review-stat"><div class="review-stat-num {'gold' if empty_n>0 else 'green'}">{empty_n}</div><div class="review-stat-label">Empty</div></div>
                <div class="review-stat"><div class="review-stat-num {'gold' if bbox_n>0 else 'green'}">{bbox_n}</div><div class="review-stat-label">Bad BBox</div></div>
                <div class="review-stat"><div class="review-stat-num {'red' if wrong_n>0 else 'green'}">{wrong_n}</div><div class="review-stat-label">Wrong Label</div></div>
            </div>
            <div style="font-size:0.65rem;color:var(--purple);letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;font-family:Cabin,sans-serif;">Completion — {pct}%</div>
            <div class="progress-bar-outer"><div class="progress-bar-inner" style="width:{pct}%;"></div></div>
        </div>""", unsafe_allow_html=True)

        flagged_entries = d.get("flagged_entries", [])
        if flagged_entries:
            with st.expander(f"View flagged images — {ps['name']}"):
                for entry in flagged_entries[:30]:
                    tags = ""
                    for iss in entry["issues"]:
                        if iss == "missing":     tags += '<span class="tag-missing">missing</span> '
                        elif iss == "empty":     tags += '<span class="tag-empty">empty</span> '
                        elif iss == "bbox":      tags += '<span class="tag-bbox">bad bbox</span> '
                        elif iss == "wrong_label": tags += '<span class="tag-wronglabel">wrong label</span> '
                    st.markdown(
                        f'<div class="img-row"><div class="img-info">{tags}'
                        f'<div class="img-name"><span style="color:var(--purple);font-weight:700;">{ps["name"]}</span>'
                        f'<span style="color:var(--border2);margin:0 8px;">—</span>'
                        f'<span style="color:var(--white);font-weight:700;">Task #{entry["task_id"]}</span></div></div></div>',
                        unsafe_allow_html=True,
                    )
                if len(flagged_entries) > 30:
                    st.caption(f"...and {len(flagged_entries)-30} more in the email report.")

    # ── Send Email Report ────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">Export Report</div>', unsafe_allow_html=True)
    st.write("")

    send_col, _ = st.columns([1, 3])
    with send_col:
        if st.button("Send Report to My Email", key="btn_send_email"):
            gu = st.session_state.get("gmail_user", "").strip()
            gp = st.session_state.get("gmail_pass", "").strip()
            te = st.session_state.get("to_email", "").strip()

            if not gu or not gp or not te:
                st.error("Fill in Gmail address, app password, and recipient email above.")
            else:
                html_body = build_html_report(project_summaries, meta)
                with st.spinner("Sending..."):
                    ok, err = send_email_report(gu, gp, te, html_body)
                if ok:
                    st.success(f"Report sent to {te}.")
                else:
                    st.error(f"Failed: {err}")

    st.markdown('</div>', unsafe_allow_html=True)
