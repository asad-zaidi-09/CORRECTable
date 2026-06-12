"""
pages/clean.py
--------------
The "Clean Dataset" page.

Flow:
  1. User pastes a folder path
  2. App scans for duplicate + blurry images (analyze_folder)
  3. Displays results in 3 columns: clean, blurry, duplicates
  4. User can export any of the three groups to their Desktop
"""

import os
import shutil

import streamlit as st

from utils.image_utils import (
    SUPPORTED,
    analyze_folder,
    image_to_base64_thumb,
)

DESKTOP = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")


# ── Small HTML helpers ──────────────────────────────────────────────────────

def _render_image_rows(items, tag_type, meta_label, folder_path):
    """Builds HTML for the small image preview rows inside the option boxes."""
    rows_html = ""
    for name, meta in items:
        filepath = os.path.join(folder_path, name)
        try:
            thumb = image_to_base64_thumb(filepath)
            short = name if len(name) <= 26 else name[:23] + "..."
            tag = (
                '<span class="tag-blurry">blurry</span>'
                if tag_type == "blurry"
                else '<span class="tag-duplicate">duplicate</span>'
            )
            rows_html += f"""
            <div class="img-row">
                <div class="img-info">{tag}
                    <div class="img-name" title="{name}">{short}</div>
                    <div class="img-meta">{meta_label}: {meta}</div>
                </div>
                <img src="data:image/jpeg;base64,{thumb}" class="img-thumb"/>
            </div>"""
        except Exception:
            rows_html += f'<div class="img-row"><div class="img-info"><div class="img-name">{name}</div></div></div>'
    return rows_html


def _render_previews(items, folder_path, meta_label):
    """Renders expandable full-size image previews using Streamlit expanders."""
    for name, meta in items:
        short = name if len(name) <= 38 else name[:35] + "..."
        with st.expander(short):
            st.image(
                os.path.join(folder_path, name),
                caption=f"{meta_label}: {meta}",
                use_column_width=True,
            )


def _export_with_progress(files, src_folder, dst_folder, label="Exporting"):
    """Copies a list of files to dst_folder with a progress bar."""
    os.makedirs(dst_folder, exist_ok=True)
    prog = st.progress(0)
    cap = st.caption(f"{label}...")
    for i, f in enumerate(files):
        shutil.copy(os.path.join(src_folder, f), os.path.join(dst_folder, f))
        prog.progress((i + 1) / len(files))
    cap.empty()


# ── Main render function ────────────────────────────────────────────────────

def render():
    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Dataset Path</div>', unsafe_allow_html=True)

    raw_path = st.text_input(
        "",
        placeholder="Paste your folder path here",
        label_visibility="collapsed",
        key="clean_path",
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
        st.error("No images found in this folder.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    st.success(f"{len(all_images)} images found.")

    # ── Run analysis (cached in session_state to avoid re-running on every widget change) ──
    if st.session_state.get("analyzed_path") != folder_path:
        st.divider()
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

    # Images that are neither duplicate nor blurry
    clean_skip = set([d[0] for d in exact_duplicates] + [b[0] for b in blurry_images])
    clean_images = [f for f in all_images if f not in clean_skip]

    # ── Metrics ──
    st.divider()
    st.markdown('<div class="section-label">Results</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-box"><div class="metric-number">{len(all_images)}</div><div class="metric-label">Total Images</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-box"><div class="metric-number">{len(exact_duplicates)}</div><div class="metric-label">Exact Duplicates</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-box"><div class="metric-number">{len(blurry_images)}</div><div class="metric-label">Blurry Images</div></div>', unsafe_allow_html=True)

    # ── Export columns ──
    st.divider()
    st.markdown('<div class="section-label">Export Options</div>', unsafe_allow_html=True)
    st.write("")
    col1, col2, col3 = st.columns(3)
    empty_row = '<div class="img-row" style="justify-content:center;"><div style="text-align:center;color:var(--text2);font-size:0.72rem;padding:16px 0;">No flagged images to preview.</div></div>'

    with col1:
        st.markdown(f"""<div class="option-box">
            <div class="option-number">Option 01</div>
            <div class="option-title">Clean Dataset</div>
            <div class="option-desc">Duplicates and blurry images removed. Ready to label.</div>
            <div class="img-count">{len(clean_images)} images ready</div>{empty_row}</div>""",
            unsafe_allow_html=True)
        if st.button("Export Clean Dataset", key="btn_clean"):
            if not clean_images:
                st.error("All images were flagged.")
            else:
                _export_with_progress(clean_images, folder_path, os.path.join(DESKTOP, "clean_dataset"))
                st.success(f"Done. {len(clean_images)} images saved.")

    with col2:
        no_blurry = '<div class="img-row" style="justify-content:center;"><div style="text-align:center;color:var(--text2);font-size:0.72rem;padding:16px 0;">No blurry images found.</div></div>'
        rows = _render_image_rows(blurry_images, "blurry", "score", folder_path) if blurry_images else no_blurry
        st.markdown(f"""<div class="option-box">
            <div class="option-number">Option 02</div>
            <div class="option-title">Blurry Images</div>
            <div class="option-desc">Too blurry to label reliably. Review before discarding.</div>
            <div class="img-count">{len(blurry_images)} flagged</div>{rows}</div>""",
            unsafe_allow_html=True)
        if blurry_images:
            _render_previews(blurry_images, folder_path, "Blur score")
        if st.button("Export Blurry Images", key="btn_blurry"):
            if not blurry_images:
                st.error("Nothing to export.")
            else:
                _export_with_progress([n for n, _ in blurry_images], folder_path, os.path.join(DESKTOP, "blurry_images"))
                st.success(f"Done. {len(blurry_images)} images saved.")

    with col3:
        no_dups = '<div class="img-row" style="justify-content:center;"><div style="text-align:center;color:var(--text2);font-size:0.72rem;padding:16px 0;">No exact duplicates found.</div></div>'
        rows = _render_image_rows(exact_duplicates, "duplicate", "original", folder_path) if exact_duplicates else no_dups
        st.markdown(f"""<div class="option-box">
            <div class="option-number">Option 03</div>
            <div class="option-title">Exact Duplicates</div>
            <div class="option-desc">Pixel-identical files. Byte-for-byte the same.</div>
            <div class="img-count">{len(exact_duplicates)} flagged</div>{rows}</div>""",
            unsafe_allow_html=True)
        if exact_duplicates:
            _render_previews(exact_duplicates, folder_path, "Original")
        if st.button("Export Exact Duplicates", key="btn_dups"):
            if not exact_duplicates:
                st.error("Nothing to export.")
            else:
                _export_with_progress([n for n, _ in exact_duplicates], folder_path, os.path.join(DESKTOP, "exact_duplicates"))
                st.success(f"Done. {len(exact_duplicates)} duplicates saved.")

    st.markdown('</div>', unsafe_allow_html=True)
