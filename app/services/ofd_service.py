"""OFD 航空运输电子客票行程单校验、结构化解析与 PDF 转换。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Optional, Tuple
import xml.etree.ElementTree as ET

from PyPDF2 import PdfReader


MAX_OFD_SIZE = 50 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 2048
MAX_MEMBER_SIZE = 32 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 128 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1000
MAX_XML_SIZE = 8 * 1024 * 1024
CONVERSION_TIMEOUT_SECONDS = 90


class OFDError(ValueError):
    """OFD 处理失败。"""


class OFDValidationError(OFDError):
    """OFD 文件结构或大小不安全。"""


class OFDConversionError(OFDError):
    """OFD 票面转换失败。"""


def _safe_member_name(name: str) -> bool:
    normalized = (name or "").replace("\\", "/")
    if not normalized or "\x00" in normalized or normalized.startswith("/"):
        return False
    # 同时拦截 Windows 盘符路径和所有父目录跳转。
    if re.match(r"^[A-Za-z]:", normalized):
        return False
    return ".." not in PurePosixPath(normalized).parts


def validate_ofd_archive(ofd_path: str) -> Tuple[zipfile.ZipInfo, ...]:
    """验证 OFD ZIP 容器，限制路径穿越、加密成员和压缩炸弹。"""
    path = Path(ofd_path)
    if not path.is_file():
        raise OFDValidationError("OFD 文件不存在")
    size = path.stat().st_size
    if size <= 0 or size > MAX_OFD_SIZE:
        raise OFDValidationError("OFD 文件为空或超过 50MB 限制")
    if not zipfile.is_zipfile(path):
        raise OFDValidationError("文件不是有效的 OFD/ZIP 容器")

    try:
        with zipfile.ZipFile(path, "r") as archive:
            entries = tuple(archive.infolist())
            if not entries or len(entries) > MAX_ARCHIVE_ENTRIES:
                raise OFDValidationError("OFD 文件条目数量异常")

            total_size = 0
            has_manifest = False
            for info in entries:
                if not _safe_member_name(info.filename):
                    raise OFDValidationError("OFD 包含不安全的文件路径")
                if info.flag_bits & 0x1:
                    raise OFDValidationError("不支持加密的 OFD 文件")
                if info.file_size > MAX_MEMBER_SIZE:
                    raise OFDValidationError("OFD 内单个文件过大")
                total_size += info.file_size
                if total_size > MAX_TOTAL_UNCOMPRESSED:
                    raise OFDValidationError("OFD 解压后总体积过大")
                if info.file_size > 1024 * 1024:
                    ratio = info.file_size / max(1, info.compress_size)
                    if ratio > MAX_COMPRESSION_RATIO:
                        raise OFDValidationError("OFD 压缩率异常")
                if info.filename.replace("\\", "/").strip("/").lower() == "ofd.xml":
                    has_manifest = True

            if not has_manifest:
                raise OFDValidationError("OFD 缺少 OFD.xml 清单")
            bad_member = archive.testzip()
            if bad_member:
                raise OFDValidationError("OFD 文件校验失败")
            return entries
    except OFDValidationError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise OFDValidationError("无法读取 OFD 文件") from exc


def _local_name(tag: str) -> str:
    return (tag or "").rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def _clean_text(value: Optional[str]) -> str:
    return " ".join((value or "").split())


def _compact_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", "", value or "")


def _first(values: Dict[str, list], key: str) -> str:
    for value in values.get(key, []):
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return ""


def _amount(value: str) -> float:
    try:
        parsed = Decimal((value or "").replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return 0.0
    if parsed < 0 or parsed > Decimal("10000000"):
        return 0.0
    return float(parsed.quantize(Decimal("0.01")))


def _xml_candidates(entries: Iterable[zipfile.ZipInfo]) -> list:
    candidates = [
        info
        for info in entries
        if not info.is_dir() and info.filename.lower().endswith(".xml")
    ]
    return sorted(
        candidates,
        key=lambda info: (0 if "/attach" in f"/{info.filename.lower()}" else 1, info.filename),
    )


def _metadata_from_xml(xml_bytes: bytes) -> Optional[dict]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None

    values: Dict[str, list] = {}
    for element in root.iter():
        name = _local_name(element.tag)
        if element.text and element.text.strip():
            values.setdefault(name, []).append(element.text)

    invoice_number = _first(values, "ElectronicInvoiceAirTransportReceiptNumber")
    ticket_number = _first(values, "ETicketNumber")
    flight_number = _compact_text(_first(values, "Flight")).upper()
    if not (invoice_number or ticket_number or flight_number):
        return None

    segments = []
    for element in root.iter():
        if _local_name(element.tag) != "DetailInformationOfAirTicketTuple":
            continue
        segment_values: Dict[str, list] = {}
        for child in element.iter():
            name = _local_name(child.tag)
            if child.text and child.text.strip():
                segment_values.setdefault(name, []).append(child.text)
        segment = {
            "from_station": _compact_text(_first(segment_values, "DepartureStation")),
            "to_station": _compact_text(_first(segment_values, "DestinationStation")),
            "flight_no": _compact_text(_first(segment_values, "Flight")).upper(),
            "carrier": _clean_text(_first(segment_values, "Carrier")),
            "travel_date": _clean_text(_first(segment_values, "CarrierDate")),
            "departure_time": _clean_text(_first(segment_values, "DepartureTime")),
            "seat_class": _clean_text(_first(segment_values, "Class")),
        }
        if any(segment.values()):
            segments.append(segment)

    first_segment = segments[0] if segments else {}
    total_amount = _amount(_first(values, "TotalAmount"))
    metadata = {
        "document_type": "flight_ticket",
        "invoice_type": "电子发票（航空运输电子客票行程单）",
        "invoice_number": invoice_number,
        "ticket_number": ticket_number,
        "amount": total_amount,
        "total_amount": total_amount,
        "flight_no": first_segment.get("flight_no") or flight_number,
        "from_station": first_segment.get("from_station") or _compact_text(_first(values, "DepartureStation")),
        "to_station": first_segment.get("to_station") or _compact_text(_first(values, "DestinationStation")),
        "travel_date": first_segment.get("travel_date") or _first(values, "CarrierDate"),
        "departure_time": first_segment.get("departure_time") or _first(values, "DepartureTime"),
        "issue_date": _first(values, "IssueDate"),
        "passenger_name": _first(values, "PassengerName"),
        "purchaser_name": _first(values, "NameOfPurchaser"),
        "seller_name": _first(values, "NameOfSeller"),
        "segments": segments,
        "source_format": "ofd",
    }
    if metadata["from_station"] and metadata["to_station"]:
        metadata["route"] = f'{metadata["from_station"]}→{metadata["to_station"]}'
    else:
        metadata["route"] = ""
    return metadata


def parse_air_itinerary_metadata(ofd_path: str) -> dict:
    """从 OFD 附件 XBRL 中提取航空电子客票行程单字段。"""
    entries = validate_ofd_archive(ofd_path)
    with zipfile.ZipFile(ofd_path, "r") as archive:
        for info in _xml_candidates(entries):
            if info.file_size > MAX_XML_SIZE:
                continue
            metadata = _metadata_from_xml(archive.read(info))
            if metadata:
                metadata["metadata_member"] = info.filename
                return metadata
    raise OFDValidationError("仅支持含航空运输电子客票 XBRL 的 OFD 文件")


def _font_path() -> str:
    candidates = [
        os.environ.get("OFD_FONT_PATH", ""),
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    # 转换工作进程还有内置中文 CID 字体兜底。
    return ""


def convert_ofd_to_pdf(ofd_path: str, output_pdf_path: str) -> str:
    """在隔离工作进程中将已验证的 OFD 票面转换为 PDF。"""
    validate_ofd_archive(ofd_path)
    source = Path(ofd_path).resolve()
    destination = Path(output_pdf_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    worker = Path(__file__).with_name("ofd_worker.py")

    with tempfile.TemporaryDirectory(prefix="order-ofd-") as work_dir:
        temporary_pdf = Path(work_dir) / "converted.pdf"
        command = [sys.executable, str(worker), str(source), str(temporary_pdf)]
        font_path = _font_path()
        if font_path:
            command.extend(["--font", font_path])
        try:
            completed = subprocess.run(
                command,
                cwd=work_dir,
                check=False,
                capture_output=True,
                text=True,
                timeout=CONVERSION_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise OFDConversionError("OFD 转 PDF 超时") from exc
        except OSError as exc:
            raise OFDConversionError("无法启动 OFD 转换程序") from exc

        if completed.returncode != 0 or not temporary_pdf.is_file():
            detail = (completed.stderr or "").strip().splitlines()
            suffix = f"：{detail[-1][:200]}" if detail else ""
            raise OFDConversionError(f"OFD 票面转换失败{suffix}")
        try:
            reader = PdfReader(str(temporary_pdf))
            if not reader.pages:
                raise OFDConversionError("OFD 转换结果没有页面")
        except OFDConversionError:
            raise
        except Exception as exc:
            raise OFDConversionError("OFD 转换结果不是有效 PDF") from exc

        staged = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        shutil.copy2(temporary_pdf, staged)
        os.replace(staged, destination)
    return str(destination)


def prepare_ofd_for_processing(
    ofd_path: str,
    output_dir: str,
    original_filename: Optional[str] = None,
) -> Tuple[str, dict]:
    """解析并转换航空电子客票 OFD，返回 PDF 路径和结构化元数据。"""
    metadata = parse_air_itinerary_metadata(ofd_path)
    metadata["source_name"] = original_filename or Path(ofd_path).name

    identity = metadata.get("invoice_number") or metadata.get("ticket_number") or uuid.uuid4().hex[:12]
    identity = re.sub(r"[^A-Za-z0-9_-]", "", str(identity))[:80] or uuid.uuid4().hex[:12]
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / f"flight_itinerary_{identity}.pdf"
    index = 2
    while output_path.exists():
        output_path = output_root / f"flight_itinerary_{identity}_{index}.pdf"
        index += 1

    convert_ofd_to_pdf(ofd_path, str(output_path))
    return str(output_path), metadata
