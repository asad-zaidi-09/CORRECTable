"""
pages/about.py
--------------
The landing/hero page. Pure HTML rendered via st.markdown.
No logic here — just content and layout.
"""

import streamlit as st


def render():
    st.markdown("""
    <div class="hero-wrapper">
        <video class="hero-video" autoplay loop muted playsinline>
            <source src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260210_031346_d87182fb-b0af-4273-84d1-c6fd17d6bf0f.mp4" type="video/mp4"/>
        </video>
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <div class="tagline-pill">
                <span class="tagline-badge">New</span>
                Dataset Quality Control — CORRECTabel v1.0
            </div>
            <div class="hero-title">
                Clean your dataset,<br/><em>label</em> with confidence
            </div>
            <div class="hero-sub">
                Purpose-built for image labeling teams. Remove duplicates, catch blurry images,
                push directly to Label Studio, and audit your labelers — all in one place.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="page-content">', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:40px;">
        <div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:28px 24px;">
            <div style="font-family:Manrope,sans-serif;font-size:2rem;font-weight:800;color:var(--border2);margin-bottom:16px;">01</div>
            <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:white;margin-bottom:10px;">Duplicate Detection</div>
            <div style="font-family:Inter,sans-serif;font-size:0.75rem;color:var(--text2);line-height:1.7;">Finds pixel-perfect identical images using MD5 hashing. Not similar — byte-for-byte the same.</div>
        </div>
        <div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:28px 24px;">
            <div style="font-family:Manrope,sans-serif;font-size:2rem;font-weight:800;color:var(--border2);margin-bottom:16px;">02</div>
            <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:white;margin-bottom:10px;">Blur Analysis</div>
            <div style="font-family:Inter,sans-serif;font-size:0.75rem;color:var(--text2);line-height:1.7;">Uses Laplacian variance to detect images too blurry to label reliably.</div>
        </div>
        <div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:28px 24px;">
            <div style="font-family:Manrope,sans-serif;font-size:2rem;font-weight:800;color:var(--border2);margin-bottom:16px;">03</div>
            <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:white;margin-bottom:10px;">Label Studio Push</div>
            <div style="font-family:Inter,sans-serif;font-size:0.75rem;color:var(--text2);line-height:1.7;">Split your dataset across labelers and push directly to Label Studio via API.</div>
        </div>
        <div style="background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:28px 24px;">
            <div style="font-family:Manrope,sans-serif;font-size:2rem;font-weight:800;color:var(--border2);margin-bottom:16px;">04</div>
            <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:white;margin-bottom:10px;">Review & Report</div>
            <div style="font-family:Inter,sans-serif;font-size:0.75rem;color:var(--text2);line-height:1.7;">Audit labelers for missing, empty, bad bounding boxes and wrong labels.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
