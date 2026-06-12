"""
pages/labelstudio.py
--------------------
The "Label Studio" page.

Flow:
  1. User connects to Label Studio (URL + API key)
  2. User pastes dataset folder path (runs clean analysis)
  3. User sets number of labelers + names + image allocations
  4. User can either:
     a. Export split folders to Desktop
     b. Push each labeler's images directly to Label Studio as separate projects
"""

import os
import random
import shutil

import requests
import streamlit as st

from utils.image_utils import SUPPORTED, analyze_folder
from utils.ls_api import ls_test_connection, ls_create_project, normalize_ls_url

DESKTOP = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")

SEGMENT_COLORS = [
    "#7b39fc","#5b20dc","#9b59ff","#3d1fa0","#6644dd",
    "#4422bb","#8833ee","#2211aa","#aa44ff","#3322cc","#bb55ee","#2233bb"
]


def render():
    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    # ── Label Studio Connection ──────────────────────────────────────────────
    st.markdown('<div class="section-label">Label Studio Connection</div>', unsafe_allow_html=True)
    st.markdown('<div class="ls-config-box">', unsafe_allow_html=True)

    ls_col1, ls_col2, ls_col3 = st.columns([2, 2, 1])
    with ls_col1:
        ls_url_val = st.text_input(
            "Label Studio URL",
            value=st.session_state.get("ls_url", "http://localhost:8080"),
            placeholder="http://localhost:8080",
            key="ls_url_input",
        )
    with ls_col2:
        ls_api_val = st.text_input(
            "API Key",
            value=st.session_state.get("ls_api_key", ""),
            placeholder="Paste your API key",
            type="password",
            key="ls_api_key_input",
        )
    with ls_col3:
        st.write("")
        st.write("")
        if st.button("Test Connection", key="btn_test_ls"):
            ok, resp = ls_test_connection(ls_url_val, ls_api_val)
            if ok:
                st.session_state.ls_url = ls_url_val
                st.session_state.ls_api_key = ls_api_val
                st.session_state.ls_connected = True
                st.success("Connected successfully.")
            else:
                st.session_state.ls_connected = False
                st.error(f"Connection failed — {resp}")

    if st.session_state.get("ls_connected"):
        st.markdown(
            f'<div class="ls-connected"><span class="ls-dot"></span> Connected — {st.session_state.get("ls_url","")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Dataset Path ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">Dataset Path</div>', unsafe_allow_html=True)
    raw_path = st.text_input(
        "",
        placeholder="Paste your folder path here",
        label_visibility="collapsed",
        key="ls_path",
    )
    folder_path = raw_path.strip().strip('"').strip("'").strip()

    if not folder_path:
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if not os.path.exists(folder_path):
        st.error(f"Wrong path — '{folder_path}' does not exist.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    all_images = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(SUPPORTED)])
    if not all_images:
        st.error("No images found.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Reuse analysis from Clean page if same folder, otherwise re-run
    if st.session_state.get("analyzed_path") != folder_path:
        st.markdown('<div class="section-label">Analyzing</div>', unsafe_allow_html=True)
        prog_bar = st.progress(0)
        exact_duplicates, blurry_images = analyze_folder(
            folder_path, all_images,
            progress_callback=lambda p: prog_bar.progress(p)
        )
        st.session_state.analyzed_path = folder_path
        st.session_state.exact_duplicates = exact_duplicates
        st.session_state.blurry_images = blurry_images
    else:
        exact_duplicates = st.session_state.exact_duplicates
        blurry_images = st.session_state.blurry_images

    clean_skip = set([d[0] for d in exact_duplicates] + [b[0] for b in blurry_images])
    clean_images = [f for f in all_images if f not in clean_skip]
    total_clean = len(clean_images)

    st.success(f"{total_clean} clean images ready.")

    # ── Split Configuration ──────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">Split & Push</div>', unsafe_allow_html=True)
    st.write("")

    split_col, _ = st.columns([1, 3])
    with split_col:
        num_labelers = st.number_input(
            "Number of labelers",
            min_value=2, max_value=12,
            value=st.session_state.get("num_labelers_val", 3),
            step=1,
            key="num_labelers_input",
        )

    n = int(num_labelers)
    alloc_key = f"allocations_{n}_{total_clean}"

    # Auto-distribute evenly on first load
    if alloc_key not in st.session_state:
        base, rem = divmod(total_clean, n)
        st.session_state[alloc_key] = [base + (1 if i < rem else 0) for i in range(n)]
        st.session_state.num_labelers_val = n

    alloc = st.session_state[alloc_key]

    # Labeler names
    st.write("")
    st.markdown('<div class="section-label" style="margin-bottom:4px;">Labeler Names</div>', unsafe_allow_html=True)
    name_cols = st.columns(n)
    labeler_names = []
    for i in range(n):
        with name_cols[i]:
            lname = st.text_input(
                "",
                value=st.session_state.get(f"lname_{i}", f"Labeler {i+1}"),
                key=f"lname_input_{i}",
                placeholder=f"Labeler {i+1}",
                label_visibility="collapsed",
            )
            labeler_names.append(lname.strip() or f"Labeler {i+1}")

    # Allocation numbers
    st.write("")
    st.markdown('<div class="section-label" style="margin-bottom:4px;">Allocations</div>', unsafe_allow_html=True)
    alloc_cols = st.columns(n)
    new_alloc = list(alloc)
    changed_idx = None

    for i in range(n):
        with alloc_cols[i]:
            color = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
            st.markdown(
                f'<div style="background:{color};border-radius:6px;padding:6px 10px;margin-bottom:6px;text-align:center;">'
                f'<div style="font-family:Manrope,sans-serif;font-weight:700;font-size:0.85rem;color:#fff;">{labeler_names[i]}</div></div>',
                unsafe_allow_html=True,
            )
            val = st.number_input(
                "Images", min_value=0, max_value=total_clean,
                value=alloc[i], step=1,
                key=f"alloc_input_{alloc_key}_{i}",
                label_visibility="visible",
            )
            if val != alloc[i]:
                changed_idx = i
            new_alloc[i] = val

    # Auto-balance when one labeler's count changes
    if changed_idx is not None:
        diff = sum(new_alloc) - total_clean
        target = n - 1 if changed_idx != n - 1 else n - 2
        remaining = total_clean - sum(new_alloc[j] for j in range(n) if j != target)
        new_alloc[target] = max(0, remaining)
        st.session_state[alloc_key] = new_alloc
        alloc = new_alloc

    total_assigned = sum(alloc)

    # Visual allocation bar
    bar_segments = ""
    cursor = 0
    for i, count in enumerate(alloc):
        pct = (count / total_clean * 100) if total_clean > 0 else 0
        color = SEGMENT_COLORS[i % len(SEGMENT_COLORS)]
        bar_segments += (
            f'<div style="position:absolute;left:{cursor:.2f}%;width:{pct:.2f}%;top:0;height:100%;'
            f'background:{color};display:flex;align-items:center;justify-content:center;'
            f'font-family:Manrope,sans-serif;font-size:0.8rem;font-weight:700;color:#fff;'
            f'overflow:hidden;min-width:2px;border-right:2px solid var(--bg);box-sizing:border-box;">'
            f'{count if pct > 5 else ""}</div>'
        )
        cursor += pct

    alloc_warning = (
        f'<div style="color:var(--gold);font-size:0.7rem;margin-top:8px;font-family:Inter,sans-serif;">'
        f'Assigned {total_assigned} / {total_clean} — adjust to match total.</div>'
        if total_assigned != total_clean else ""
    )
    chips = "".join([
        f'<div style="font-family:Cabin,sans-serif;font-size:0.68rem;color:{SEGMENT_COLORS[i%len(SEGMENT_COLORS)]};'
        f'background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;">'
        f'{labeler_names[i]}: <span style="color:var(--text);">{alloc[i]} imgs</span></div>'
        for i in range(n)
    ])

    st.markdown(f"""<div class="split-bar-container">
        <div style="font-size:0.7rem;color:var(--purple);margin-bottom:10px;letter-spacing:2px;text-transform:uppercase;font-family:Cabin,sans-serif;">
            Allocation Preview — {total_clean} clean images</div>
        <div style="position:relative;height:48px;border-radius:6px;overflow:hidden;background:var(--bg3);margin-bottom:10px;">{bar_segments}</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">{chips}</div>{alloc_warning}
    </div>""", unsafe_allow_html=True)

    # ── Action Buttons ───────────────────────────────────────────────────────
    st.write("")
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("Export Split to Desktop", key="btn_split_export"):
            if total_assigned != total_clean:
                st.error(f"Fix allocation: {total_assigned} / {total_clean}.")
            elif total_clean == 0:
                st.error("No clean images.")
            else:
                shuffled = clean_images.copy()
                random.shuffle(shuffled)
                split_root = os.path.join(DESKTOP, "split_dataset")
                os.makedirs(split_root, exist_ok=True)
                prog = st.progress(0)
                cap = st.caption("Exporting...")
                cursor_i, copied = 0, 0
                for i, lname in enumerate(labeler_names):
                    chunk = shuffled[cursor_i: cursor_i + alloc[i]]
                    cursor_i += alloc[i]
                    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in lname)
                    lf = os.path.join(split_root, safe)
                    os.makedirs(lf, exist_ok=True)
                    for fname in chunk:
                        shutil.copy(os.path.join(folder_path, fname), os.path.join(lf, fname))
                        copied += 1
                        prog.progress(copied / total_clean)
                cap.empty()
                st.success(f"Done. {total_clean} images split into {n} folders.")

    with btn_col2:
        if st.button("Push to Label Studio", key="btn_push_ls"):
            if not st.session_state.get("ls_connected"):
                st.error("Connect to Label Studio first.")
            elif total_assigned != total_clean:
                st.error(f"Fix allocation: {total_assigned} / {total_clean}.")
            elif total_clean == 0:
                st.error("No clean images.")
            else:
                ls_url_s = st.session_state["ls_url"]
                ls_api_s = st.session_state["ls_api_key"]
                shuffled = clean_images.copy()
                random.shuffle(shuffled)

                overall_prog = st.progress(0)
                status_text = st.empty()
                results_log = []
                total_uploaded = 0
                cursor_i = 0
                all_ok = True

                for i, lname in enumerate(labeler_names):
                    count = alloc[i]
                    chunk = shuffled[cursor_i: cursor_i + count]
                    cursor_i += count

                    status_text.markdown(
                        f'<div style="font-size:0.75rem;color:var(--text2);">Creating project for <span style="color:var(--text);">{lname}</span>...</div>',
                        unsafe_allow_html=True,
                    )
                    project_id, err = ls_create_project(ls_url_s, ls_api_s, lname)
                    if err:
                        results_log.append(("err", f"{lname}: project creation failed — {err}"))
                        all_ok = False
                        overall_prog.progress(cursor_i / total_clean)
                        continue

                    uploaded_count = 0
                    errors = []
                    for j, fname in enumerate(chunk):
                        img_path = os.path.join(folder_path, fname)
                        ext = fname.lower().rsplit(".", 1)[-1]
                        mime = "image/png" if ext == "png" else "image/jpeg"
                        try:
                            with open(img_path, "rb") as f:
                                r = requests.post(
                                    f"{ls_url_s}/api/projects/{project_id}/import",
                                    headers={"Authorization": f"Token {ls_api_s}"},
                                    files=[("file", (fname, f, mime))],
                                    timeout=60,
                                )
                            if r.status_code in (200, 201):
                                uploaded_count += 1
                            else:
                                errors.append(f"{fname}: HTTP {r.status_code}")
                        except Exception as e:
                            errors.append(f"{fname}: {str(e)[:80]}")

                        overall_prog.progress((cursor_i - count + j + 1) / total_clean)
                        status_text.markdown(
                            f'<div style="font-size:0.75rem;color:var(--text2);">Uploading to <span style="color:var(--text);">{lname}</span>: {j+1}/{count}</div>',
                            unsafe_allow_html=True,
                        )

                    total_uploaded += uploaded_count
                    if errors:
                        results_log.append(("warn", f"{lname}: {uploaded_count}/{count} uploaded — project #{project_id} ({len(errors)} errors)"))
                    else:
                        results_log.append(("ok", f"{lname}: {uploaded_count}/{count} uploaded — project #{project_id}"))

                overall_prog.progress(1.0)
                status_text.empty()
                st.divider()
                st.markdown('<div class="section-label">Upload Results</div>', unsafe_allow_html=True)
                for kind, line in results_log:
                    if kind == "ok":
                        st.success(line)
                    elif kind == "warn":
                        st.warning(line)
                    else:
                        st.error(line)
                if all_ok:
                    st.success(f"All done. {total_uploaded} images pushed to {n} Label Studio projects.")

    st.markdown('</div>', unsafe_allow_html=True)
