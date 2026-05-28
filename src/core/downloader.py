from __future__ import annotations

import tempfile
from pathlib import Path

import requests

from src.core.parsers import parse_source1_all
from src.core.constants import SOURCE1_DEFAULT_URL


def download_source1(url: str = SOURCE1_DEFAULT_URL) -> dict[str, dict[str, dict]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()

    suffix = _infer_ext(resp)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        return parse_source1_all(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _infer_ext(resp: requests.Response) -> str:
    ct = (resp.headers.get("content-type") or "").lower()
    if "spreadsheetml" in ct or "openxmlformats" in ct:
        return ".xlsx"
    if "excel" in ct:
        return ".xls"
    cd = resp.headers.get("content-disposition") or ""
    if ".xlsx" in cd:
        return ".xlsx"
    if ".xls" in cd:
        return ".xls"
    return ".xls"
