#!/usr/bin/env python3
"""
test_xx: 火车票 PDF 信息提取实验脚本

用途:
1) 支持输入 zip/pdf 路径
2) 尝试提取: 订单名、车次、金额、起终点
3) 输出可读 JSON，便于比对规则是否稳定
"""

import io
import json
import re
import sys
import zipfile
from pathlib import Path

from PyPDF2 import PdfReader


def extract_amount(text: str) -> float:
    patterns = [
        r"[¥￥]\s*(\d+\.\d{1,2})",
        r"票价[：:\s]*([0-9]+\.[0-9]{1,2})",
        r"票面金额[：:\s]*([0-9]+\.[0-9]{1,2})",
        r"价税合计[：:\s]*([0-9]+\.[0-9]{1,2})",
        r"(\d+\.\d{1,2})\s*元",
        r"(\d+\.\d{1,2})",
    ]
    vals = []
    for p in patterns:
        for m in re.findall(p, text, flags=re.IGNORECASE):
            try:
                v = float(m)
            except Exception:
                continue
            if 1 <= v <= 10000:
                vals.append(v)
    return max(vals) if vals else 0.0


def extract_meta(text: str, source_name: str) -> dict:
    train_no = ""
    m_no = re.search(r"\b([GDCZTK]\d{1,4})\b", text, flags=re.IGNORECASE)
    if m_no:
        train_no = m_no.group(1).upper()

    from_station = ""
    to_station = ""
    m_from = re.search(r"\b([A-Za-z]{3,})\s*[GDCZTK]\d{1,4}\b", text)
    if m_from:
        from_station = m_from.group(1)
    if train_no:
        m_to = re.search(rf"\b{re.escape(train_no)}\b.*?\b([A-Za-z]{{3,}})\b", text, flags=re.IGNORECASE | re.DOTALL)
        if m_to:
            to_station = m_to.group(1)

    display_name = Path(source_name).stem
    if train_no:
        display_name = f"{display_name}-{train_no}"
    if from_station and to_station and from_station.lower() != to_station.lower():
        display_name = f"{display_name} ({from_station}→{to_station})"

    return {
        "order_id": Path(source_name).stem,
        "display_name": display_name,
        "train_no": train_no,
        "from_station": from_station,
        "to_station": to_station,
        "amount": extract_amount(text),
    }


def inspect_pdf_bytes(raw: bytes, source_name: str):
    reader = PdfReader(io.BytesIO(raw))
    rows = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        meta = extract_meta(text, source_name)
        meta["page_no"] = i
        meta["preview"] = text.replace("\n", " ")[:240]
        rows.append(meta)
    return rows


def inspect_path(path: Path):
    if path.suffix.lower() == ".zip":
        out = []
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if name.lower().endswith(".pdf"):
                    out.extend(inspect_pdf_bytes(zf.read(name), name))
        return out
    if path.suffix.lower() == ".pdf":
        return inspect_pdf_bytes(path.read_bytes(), path.name)
    return []


def main():
    if len(sys.argv) < 2:
        print("用法: python test_train_extract_info_xx.py <zip_or_pdf> [more_files...]")
        return 1

    result = {}
    for p in sys.argv[1:]:
        path = Path(p)
        result[str(path)] = inspect_path(path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
