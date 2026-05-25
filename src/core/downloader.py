from __future__ import annotations

import tempfile
from pathlib import Path

import requests

from src.core.parsers import parse_source1_all


SOURCE1_DEFAULT_URL = (
    'http://appweb.cipsa.com.pe:8054/AlmacenStock/DownLoadFiles'
    '?value={"linea":"0101","parametroX2":"","parametroX1":"0"}'
)


def download_source1(url: str = SOURCE1_DEFAULT_URL) -> dict[str, dict[str, dict]]:
    resp = requests.get(url, timeout=60)
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
