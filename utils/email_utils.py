"""
utils/email_utils.py
--------------------
Handles building the HTML email report and sending it via Gmail SMTP.

Why Gmail SMTP?
  - Free, no extra service needed
  - Requires a Gmail "App Password" (not your real password)
  - Uses port 465 with SSL encryption
"""

import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email_report(gmail_user: str, gmail_app_password: str,
                      to_email: str, html_body: str):
    """
    Sends an HTML email via Gmail's SMTP server.

    Args:
        gmail_user:          Your Gmail address (e.g. you@gmail.com)
        gmail_app_password:  16-char app password from Google Account settings
        to_email:            Recipient address
        html_body:           Full HTML string for the email body

    Returns:
        (True, None) on success
        (False, error_string) on failure

    How SMTP_SSL works:
        - Opens an encrypted connection on port 465
        - Logs in with your Gmail credentials
        - Sends the message and closes the connection
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "CORRECTabel — Labeling Review Report"
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, to_email, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def build_html_report(project_summaries: list, review_meta: dict) -> str:
    """
    Builds a self-contained dark-mode HTML email from the review results.

    Args:
        project_summaries: list of dicts from the review page
        review_meta:       dict with total_projects, total_tasks, total_issues

    Returns:
        HTML string ready to be emailed
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def issue_badge(issue_type):
        styles = {
            "missing":     ("background:#1f0a0a;color:#f87171;border:1px solid #4a1a1a;", "MISSING"),
            "empty":       ("background:#1f1008;color:#fb923c;border:1px solid #4a2a10;", "EMPTY"),
            "bbox":        ("background:#1a1200;color:#f0a030;border:1px solid #3a2800;", "BAD BBOX"),
            "wrong_label": ("background:rgba(123,57,252,0.15);color:#a484d7;border:1px solid rgba(164,132,215,0.4);", "WRONG LABEL"),
        }
        s, label = styles.get(issue_type, ("", issue_type.upper()))
        return f'<span style="{s}padding:2px 8px;border-radius:4px;font-size:10px;font-family:monospace;letter-spacing:1px;margin-right:4px;">{label}</span>'

    def stat_box(num, label, color="#ffffff"):
        return f'''<div style="background:#13101f;border:1px solid #2a2444;border-radius:8px;padding:12px 8px;text-align:center;flex:1;min-width:60px;max-width:100%;">
            <div style="font-family:'Manrope',sans-serif;font-size:20px;font-weight:800;color:{color};">{num}</div>
            <div style="font-size:8px;color:#9b96b8;text-transform:uppercase;letter-spacing:1px;margin-top:4px;font-family:monospace;word-break:break-word;">{label}</div>
        </div>'''

    project_blocks = ""
    for ps in project_summaries:
        d = ps["data"]
        issues    = ps["issues"]
        missing_n = d["unlabeled_count"]
        empty_n   = len(d["empty_annotation"])
        bbox_n    = len(d["suspicious_bbox"])
        wrong_n   = len(d["wrong_label"])
        pct       = d["completion_pct"]
        issue_color = "#f87171" if issues > 0 else "#4ade80"

        flagged_rows = ""
        for entry in d.get("flagged_entries", []):
            badges = "".join(issue_badge(i) for i in entry["issues"])
            flagged_rows += f'''<tr style="border-bottom:1px solid #1a1630;">
                <td style="padding:8px 10px;font-family:monospace;font-size:12px;color:#e2dff0;white-space:nowrap;">
                    <span style="color:#7b39fc;font-weight:700;">{ps["name"]}</span>
                    <span style="color:#3d3660;margin:0 6px;">—</span>
                    <span style="color:#ffffff;font-weight:700;">Task #{entry["task_id"]}</span>
                </td>
                <td style="padding:8px 10px;">{badges}</td>
            </tr>'''

        flagged_table = ""
        if flagged_rows:
            flagged_table = f'''<div style="margin-top:16px;">
                <div style="font-size:9px;color:#7b39fc;letter-spacing:3px;text-transform:uppercase;margin-bottom:10px;font-family:monospace;">Flagged Images</div>
                <table style="width:100%;border-collapse:collapse;background:#0d0b14;border-radius:6px;overflow:hidden;">
                    <tr style="border-bottom:1px solid #2a2444;">
                        <th style="text-align:left;padding:6px 10px;font-size:9px;color:#7b39fc;font-weight:normal;font-family:monospace;letter-spacing:2px;">LABELER — TASK</th>
                        <th style="text-align:left;padding:6px 10px;font-size:9px;color:#7b39fc;font-weight:normal;font-family:monospace;letter-spacing:2px;">ISSUE</th>
                    </tr>
                    {flagged_rows}
                </table>
            </div>'''

        project_blocks += f'''<div style="background:#13101f;border:1px solid #2a2444;border-radius:12px;padding:24px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #2a2444;">
                <div>
                    <div style="font-family:'Manrope',sans-serif;font-size:16px;font-weight:700;color:#ffffff;">{ps["name"]}</div>
                    <div style="font-size:10px;color:#9b96b8;margin-top:4px;font-family:monospace;">Project ID: {ps["project_id"]} &nbsp;·&nbsp; {d["total"]} images</div>
                </div>
                <div style="background:{'#1f0a0a' if issues > 0 else '#0a1f12'};border:1px solid {'#4a1a1a' if issues > 0 else '#1a4a28'};color:{issue_color};font-size:10px;font-family:monospace;letter-spacing:2px;padding:4px 12px;border-radius:6px;">{issues} ISSUES</div>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
                {stat_box(d["total"],  "Total")}
                {stat_box(d["labeled"], "Labeled",    "#4ade80")}
                {stat_box(missing_n,   "Missing",     "#f87171" if missing_n > 0 else "#4ade80")}
                {stat_box(empty_n,     "Empty",       "#fb923c" if empty_n   > 0 else "#4ade80")}
                {stat_box(bbox_n,      "Bad BBox",    "#f0a030" if bbox_n    > 0 else "#4ade80")}
                {stat_box(wrong_n,     "Wrong Label", "#f87171" if wrong_n   > 0 else "#4ade80")}
                {stat_box(f"{pct}%",   "Complete",    "#7b39fc")}
            </div>
            <div style="margin-top:12px;">
                <div style="font-size:9px;color:#7b39fc;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px;font-family:monospace;">Completion — {pct}%</div>
                <div style="background:#1a1630;border:1px solid #2a2444;border-radius:4px;height:6px;overflow:hidden;">
                    <div style="height:100%;border-radius:4px;background:#7b39fc;width:{pct}%;"></div>
                </div>
            </div>
            {flagged_table}
        </div>'''

    return f"""<!DOCTYPE html>
<html>
<body style="background:#0d0b14;margin:0;padding:24px;font-family:'Inter',sans-serif;">
    <div style="max-width:700px;margin:0 auto;">
        <div style="margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid #2a2444;">
            <div style="font-family:'Manrope',sans-serif;font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-1px;">
                CORRECT<span style="color:#7b39fc;">abel</span>
            </div>
            <div style="font-size:10px;color:#9b96b8;margin-top:6px;letter-spacing:3px;text-transform:uppercase;font-family:monospace;">
                Review Report — {now}
            </div>
        </div>
        <div style="background:#13101f;border:1px solid #2a2444;border-radius:12px;padding:20px;margin-bottom:24px;">
            <div style="font-size:9px;color:#7b39fc;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;font-family:monospace;">Overall Summary</div>
            <div style="display:flex;gap:16px;flex-wrap:wrap;">
                <div style="font-size:13px;color:#e2dff0;">{review_meta["total_projects"]} projects reviewed</div>
                <div style="color:#2a2444;">|</div>
                <div style="font-size:13px;color:#e2dff0;">{review_meta["total_tasks"]} total images</div>
                <div style="color:#2a2444;">|</div>
                <div style="font-size:13px;color:#e2dff0;">{review_meta["total_issues"]} total issues found</div>
            </div>
        </div>
        {project_blocks}
        <div style="margin-top:24px;padding-top:16px;border-top:1px solid #2a2444;font-size:10px;color:#55506e;text-align:center;letter-spacing:2px;font-family:monospace;">
            Generated by CORRECTabel · {now}
        </div>
    </div>
</body>
</html>"""
