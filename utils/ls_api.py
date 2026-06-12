"""
utils/ls_api.py
---------------
All communication with the Label Studio REST API.
No Streamlit code here — just HTTP requests and data parsing.

Label Studio API docs: https://labelstud.io/api
"""

import requests
from urllib.parse import urlparse


def normalize_ls_url(url: str):
    """
    Strips trailing slashes and validates the URL has a scheme + host.
    Returns (clean_url, error_message) — error is None if valid.

    Example:
        "http://localhost:8080/extra/" → "http://localhost:8080", None
        "localhost:8080"              → None, "URL must include http://"
    """
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        return None, "URL must include http:// or https://"
    if not parsed.netloc:
        return None, "URL must include a host and port"
    return f"{parsed.scheme}://{parsed.netloc}", None


def ls_headers(api_key: str) -> dict:
    """Builds the auth headers required by every Label Studio API call."""
    return {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def ls_test_connection(url: str, api_key: str):
    """
    Pings /api/projects to verify the URL + API key are valid.
    Returns (True, response) or (False, error_string).
    """
    normalized_url, err = normalize_ls_url(url)
    if err:
        return False, err
    try:
        r = requests.get(
            f"{normalized_url}/api/projects",
            headers=ls_headers(api_key),
            timeout=5,
        )
    except Exception as e:
        return False, str(e)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    return True, r


def ls_create_project(url: str, api_key: str, name: str):
    """
    Creates a new Label Studio project with a basic bounding-box config.
    Returns (project_id, None) on success, (None, error_string) on failure.

    The labeling_config XML defines the annotation interface:
    - <Image> = the image input
    - <RectangleLabels> = draw bounding boxes with a label
    """
    normalized_url, err = normalize_ls_url(url)
    if err:
        return None, err

    labeling_config = """<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="Object" background="#FF0000"/>
  </RectangleLabels>
</View>"""

    payload = {
        "title": name,
        "label_config": labeling_config,
        "description": "Auto-created by CORRECTabel",
    }

    try:
        r = requests.post(
            f"{normalized_url}/api/projects",
            headers=ls_headers(api_key),
            json=payload,
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        return None, "Could not reach Label Studio"
    except requests.exceptions.Timeout:
        return None, "Request timed out"

    if r.status_code in (200, 201):
        try:
            return r.json()["id"], None
        except Exception:
            return None, f"Bad response: {r.text[:200]}"

    return None, f"HTTP {r.status_code}: {r.text[:200]}"


def ls_get_projects(url: str, api_key: str):
    """
    Fetches all projects from Label Studio (up to 100).
    Returns (list_of_projects, None) or (None, error_string).
    """
    normalized_url, err = normalize_ls_url(url)
    if err:
        return None, err
    try:
        r = requests.get(
            f"{normalized_url}/api/projects?page_size=100",
            headers=ls_headers(api_key),
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("results", []), None
        return None, f"HTTP {r.status_code}"
    except Exception as e:
        return None, str(e)


def ls_get_tasks(url: str, api_key: str, project_id: int):
    """
    Fetches all tasks (images) in a project.
    Returns (list_of_tasks, None) or ([], error_string).

    A "task" in Label Studio = one image + its annotations.
    """
    normalized_url, _ = normalize_ls_url(url)
    try:
        r = requests.get(
            f"{normalized_url}/api/tasks?project={project_id}&page_size=1000",
            headers=ls_headers(api_key),
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data, None
            return data.get("tasks", data.get("results", [])), None
        return [], f"HTTP {r.status_code}"
    except Exception as e:
        return [], str(e)


def ls_get_annotations(url: str, api_key: str, task_id: int):
    """
    Fetches annotations for a single task.
    Returns (list_of_annotations, None) or ([], error_string).
    """
    normalized_url, _ = normalize_ls_url(url)
    try:
        r = requests.get(
            f"{normalized_url}/api/tasks/{task_id}/annotations",
            headers=ls_headers(api_key),
            timeout=10,
        )
        if r.status_code == 200:
            return r.json(), None
        return [], f"HTTP {r.status_code}"
    except Exception as e:
        return [], str(e)


def analyze_project(url: str, api_key: str, project: dict,
                    expected_labels=None, bbox_min_area: float = 1.0):
    """
    Audits a single Label Studio project for annotation quality issues.

    Checks performed per task:
      - missing     → task has no annotations at all
      - empty       → annotation exists but has no drawn shapes
      - bbox        → bounding box area is below bbox_min_area %
      - wrong_label → label used is not in expected_labels list

    Returns a summary dict, or (None, error_string) on failure.

    bbox_min_area explanation:
      Label Studio stores bbox width/height as percentages (0–100).
      area = (width * height) / 100  → gives area as a % of image
      If area < bbox_min_area, it's suspiciously small (likely an accident).
    """
    project_id = project["id"]
    tasks, err = ls_get_tasks(url, api_key, project_id)
    if err:
        return None, err

    tasks_sorted = sorted(tasks, key=lambda t: t["id"])
    total = len(tasks_sorted)

    labeled_count = 0
    unlabeled_count = 0
    empty_annotation_count = 0
    suspicious_bbox_count = 0
    wrong_label_count = 0
    flagged_entries = []

    for task in tasks_sorted:
        task_id = task["id"]
        filename = os.path.basename(
            task.get("data", {}).get(
                "image", task.get("data", {}).get("url", f"task_{task_id}")
            )
        )

        annotations = task.get("annotations", [])
        if not annotations:
            annotations, _ = ls_get_annotations(url, api_key, task_id)

        # ── No annotations at all ──
        if not annotations:
            unlabeled_count += 1
            flagged_entries.append({"task_id": task_id, "filename": filename, "issues": ["missing"]})
            continue

        labeled_count += 1
        task_issues = []

        for ann in annotations:
            results = ann.get("result", [])

            # ── Annotation exists but is empty (no shapes drawn) ──
            if not results:
                if "empty" not in task_issues:
                    empty_annotation_count += 1
                    task_issues.append("empty")
                continue

            for res in results:
                rv = res.get("value", {})

                # ── Suspiciously small bounding box ──
                area = (rv.get("width", 100) * rv.get("height", 100)) / 100.0
                if area < bbox_min_area:
                    if "bbox" not in task_issues:
                        suspicious_bbox_count += 1
                        task_issues.append("bbox")

                # ── Wrong label class ──
                if expected_labels:
                    for lbl in rv.get("rectanglelabels", []):
                        if lbl not in expected_labels:
                            if "wrong_label" not in task_issues:
                                wrong_label_count += 1
                                task_issues.append("wrong_label")

        if task_issues:
            flagged_entries.append({"task_id": task_id, "filename": filename, "issues": task_issues})

    return {
        "total": total,
        "labeled": labeled_count,
        "unlabeled_count": unlabeled_count,
        "empty_annotation": ["_"] * empty_annotation_count,
        "suspicious_bbox": ["_"] * suspicious_bbox_count,
        "wrong_label": ["_"] * wrong_label_count,
        "flagged_entries": flagged_entries,
        "completion_pct": round((labeled_count / total * 100) if total > 0 else 0, 1),
    }, None


# Needed for filename extraction inside analyze_project
import os
