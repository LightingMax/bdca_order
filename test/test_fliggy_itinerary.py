#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞猪旅行电子客票行程单：可替代发票，ZIP 和 PDF 都能当机票打印。"""

import io
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pdf_service import (  # noqa: E402
    identify_zip_type_from_filename,
    looks_like_flight_itinerary,
    looks_like_toll_invoice,
)

REAL_ZIP = PROJECT_ROOT / "temp_files" / "飞猪旅行电子报销凭证.zip"


def _decode_zip_name(name):
    try:
        return name.encode("cp437").decode("gbk")
    except Exception:
        return name


def _extract_real_pdf(dest_dir, dest_name="飞猪电子行程单.pdf"):
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / dest_name
    with zipfile.ZipFile(REAL_ZIP) as zf:
        for info in zf.infolist():
            name = _decode_zip_name(info.filename)
            if name.lower().endswith(".pdf"):
                dest.write_bytes(zf.read(info))
                return dest, name
    raise FileNotFoundError("zip 内没有 PDF")


def _build_test_app(tmp_dir):
    from app import create_app

    tmp_dir = Path(tmp_dir)
    app = create_app()
    folders = {
        "TEMP_FOLDER": tmp_dir / "temp",
        "OUTPUT_FOLDER": tmp_dir / "output",
        "DATA_FOLDER": tmp_dir / "data",
        "UPLOAD_FOLDER": tmp_dir / "uploads",
        "LOG_FOLDER": tmp_dir / "logs",
    }
    for path in folders.values():
        path.mkdir(parents=True, exist_ok=True)
    app.config.update(
        TESTING=True,
        SECRET_KEY="fliggy-itinerary-test",
        TEMP_FOLDER=str(folders["TEMP_FOLDER"]),
        OUTPUT_FOLDER=str(folders["OUTPUT_FOLDER"]),
        DATA_FOLDER=str(folders["DATA_FOLDER"]),
        UPLOAD_FOLDER=str(folders["UPLOAD_FOLDER"]),
        LOG_FOLDER=str(folders["LOG_FOLDER"]),
        USER_DATA_FILE=str(folders["DATA_FOLDER"] / "user_data.json"),
        GLOBAL_STATS_FILE=str(folders["DATA_FOLDER"] / "global_stats.json"),
        PROJECT_ROOT=str(tmp_dir),
    )
    return app


class FliggyItineraryRuleTests(unittest.TestCase):
    def test_zip_and_pdf_names(self):
        self.assertTrue(looks_like_flight_itinerary(zip_filename="飞猪旅行电子报销凭证.zip"))
        self.assertTrue(
            looks_like_flight_itinerary(
                name="【飞猪】重庆-杭州  订单10143835988961-机票款凭证 电子行程单.pdf"
            )
        )
        self.assertTrue(
            looks_like_flight_itinerary(text="电子发票（航空运输电子客票行程单） 航班号 CZ2389")
        )
        self.assertFalse(looks_like_flight_itinerary(name="电子行程单.pdf"))
        self.assertFalse(
            looks_like_flight_itinerary(
                name="【及时用车-53.21元-2个行程】高德打车电子发票.pdf",
                text="电子行程单 过路费",
            )
        )
        self.assertFalse(looks_like_toll_invoice(name="飞猪旅行电子报销凭证.zip"))

    def test_zip_type_is_flight_not_taxi(self):
        self.assertEqual(identify_zip_type_from_filename("飞猪旅行电子报销凭证.zip"), "flight")
        self.assertEqual(identify_zip_type_from_filename("飞猪电子行程单.zip"), "flight")
        self.assertEqual(identify_zip_type_from_filename("高德打车电子行程单.zip"), "taxi")


class FliggyItineraryProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REAL_ZIP.exists():
            raise unittest.SkipTest(f"缺少真实飞猪样本: {REAL_ZIP}")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        self.tmp.cleanup()

    def test_identify_extracted_pdf_and_zip_name(self):
        from app.services.pdf_service import identify_pdf_type

        pdf_path, inner_name = _extract_real_pdf(self.tmp.name)
        self.assertEqual(identify_pdf_type(str(pdf_path), zip_filename=inner_name), "flight_ticket")
        self.assertEqual(
            identify_pdf_type(str(pdf_path), zip_filename="飞猪旅行电子报销凭证.zip"),
            "flight_ticket",
        )
        renamed = Path(self.tmp.name) / "电子行程单.pdf"
        shutil.copy2(pdf_path, renamed)
        self.assertEqual(
            identify_pdf_type(str(renamed), zip_filename="飞猪旅行电子报销凭证.zip"),
            "flight_ticket",
        )

    def test_process_zip_contents_as_flight_ticket(self):
        from app.services.file_service import extract_zip
        from app.services.pdf_service import process_pdf_files
        from PyPDF2 import PdfReader

        extract_dir = Path(self.tmp.name) / "extracted"
        extract_dir.mkdir()
        extract_zip(str(REAL_ZIP), str(extract_dir))
        results, _, info = process_pdf_files(str(extract_dir), "飞猪旅行电子报销凭证.zip")
        self.assertEqual(len(results), 1, results)
        result = results[0]
        self.assertTrue(result.get("has_flight_ticket"))
        self.assertFalse(result.get("has_itinerary"))
        self.assertEqual(result.get("combined_type"), "flight_single")
        self.assertEqual(result.get("amount"), 790.00)
        self.assertEqual(result.get("flight_amount"), 790.00)
        items = result.get("train_ticket_items") or []
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get("flight_no"), "CZ2389")
        self.assertEqual(items[0].get("from_station"), "重庆")
        self.assertEqual(items[0].get("to_station"), "杭州")
        output_path = Path(self.app.config["OUTPUT_FOLDER"]) / result["output_file"]
        self.assertTrue(output_path.exists())
        self.assertEqual(len(PdfReader(str(output_path)).pages), 1)
        self.assertEqual(info.get("flight_tickets"), 1)
        self.assertEqual(info.get("flight_amount"), 790.00)

    def test_two_itineraries_print_on_one_page(self):
        from app.services.pdf_service import process_pdf_files
        from PyPDF2 import PdfReader

        extract_dir = Path(self.tmp.name) / "extract"
        pdf_path, _inner = _extract_real_pdf(extract_dir, "去程-机票款凭证 电子行程单.pdf")
        shutil.copy2(pdf_path, extract_dir / "回程-机票款凭证 电子行程单.pdf")
        results, _, info = process_pdf_files(str(extract_dir), "飞猪旅行电子报销凭证.zip")
        self.assertEqual(len(results), 1, results)
        result = results[0]
        self.assertEqual(result.get("combined_type"), "ticket_double")
        self.assertEqual(result.get("flight_ticket_count"), 2)
        self.assertEqual(result.get("amount"), 1580.00)
        self.assertEqual(result.get("page_count"), 1)
        output_path = Path(self.app.config["OUTPUT_FOLDER"]) / result["output_file"]
        self.assertEqual(len(PdfReader(str(output_path)).pages), 1)
        self.assertEqual(info.get("flight_tickets"), 2)


class FliggyItineraryUploadApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REAL_ZIP.exists():
            raise unittest.SkipTest(f"缺少真实飞猪样本: {REAL_ZIP}")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_upload_zip(self):
        buf = io.BytesIO(REAL_ZIP.read_bytes())
        response = self.client.post(
            "/api/upload",
            data={"files": [(buf, REAL_ZIP.name)]},
            content_type="multipart/form-data",
        )
        buf.close()
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload.get("success"))
        results = payload.get("results") or []
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].get("has_flight_ticket"))
        self.assertEqual(results[0].get("amount"), 790.00)
        self.assertEqual(payload["current_session"]["flight_amount"], 790.00)
        self.assertEqual(payload["current_session"]["taxi_amount"], 0)

    def test_upload_inner_pdf(self):
        pdf_path, inner_name = _extract_real_pdf(self.tmp.name)
        buf = io.BytesIO(pdf_path.read_bytes())
        response = self.client.post(
            "/api/upload",
            data={"files": [(buf, inner_name)]},
            content_type="multipart/form-data",
        )
        buf.close()
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload.get("success"))
        results = payload.get("results") or []
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].get("has_flight_ticket"))
        self.assertEqual(results[0].get("amount"), 790.00)
        self.assertEqual(results[0].get("combined_type"), "flight_single")


if __name__ == "__main__":
    unittest.main(verbosity=2)
