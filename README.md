# CORRECTabel

**Dataset quality control for image labeling teams.**

CORRECTabel is a Streamlit app that helps you clean your image dataset, distribute it across labelers, push it directly to Label Studio, and audit annotation quality — all in one place.

---

## Features

| Feature | What it does |
|---|---|
| **Duplicate Detection** | Finds byte-for-byte identical images using MD5 hashing |
| **Blur Analysis** | Flags images too blurry to label using Laplacian variance |
| **Label Studio Push** | Splits your dataset across labelers and pushes via the LS API |
| **Review & Report** | Audits each labeler for missing, empty, bad bbox, and wrong label issues |
| **Email Report** | Sends a formatted HTML review report via Gmail |

---

## Project Structure

```
CORRECTabel/
├── app.py                  # Entry point
├── requirements.txt
├── .gitignore
│
├── styles/
│   └── main.css            # All custom CSS
│
├── pages/
│   ├── about.py            # Landing page
│   ├── clean.py            # Dataset cleaning page
│   ├── labelstudio.py      # LS push page
│   └── review.py           # Annotation review page
│
└── utils/
    ├── image_utils.py      # Blur + duplicate detection, thumbnails
    ├── ls_api.py           # Label Studio REST API calls
    └── email_utils.py      # Gmail SMTP + HTML report builder
```

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/CORRECTabel.git
cd CORRECTabel
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

---

## Requirements

- Python 3.9+
- A running [Label Studio](https://labelstud.io/) instance (local or hosted)
- A Gmail account with [App Passwords](https://support.google.com/accounts/answer/185833) enabled (for email reports)

---

## How the blur detection works

Images are scored using **Laplacian variance**:
- The image is converted to grayscale
- A Laplacian filter (edge detector) is applied
- The variance of the result is computed
- **Low variance = blurry** (few sharp edges), **high variance = sharp**
- Default threshold: score < 30 is flagged as blurry

## How duplicate detection works

Each image is read as raw bytes and hashed with **MD5**. If two files produce the same hash, they are byte-for-byte identical. This catches exact copies regardless of filename.

---

## Deployment

### Streamlit Cloud (recommended for demos)
1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as the entry point
4. Deploy

> **Note:** Streamlit Cloud runs on Linux. The `export to Desktop` features write to a cloud path, not your local machine. For full local export functionality, run the app locally.

---

## Tech Stack

- [Streamlit](https://streamlit.io/) — UI framework
- [OpenCV](https://opencv.org/) — Blur detection (Laplacian variance)
- [Pillow](https://pillow.readthedocs.io/) — Image thumbnails
- [Label Studio API](https://labelstud.io/api) — Project creation + task upload
- Gmail SMTP — Email report delivery
