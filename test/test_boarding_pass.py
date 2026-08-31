#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""航旅纵横个人登机凭证：识别为机票，并与火车票/机票按两张一页合并。"""

import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pdf_service import (  # noqa: E402
    identify_zip_type_from_filename,
    looks_like_boarding_pass,
)

REAL_BOARDING_PASS = PROJECT_ROOT / "temp_files" / "个人登机凭证.pdf"


def _make_pdf_bytes(text="electronic invoice"):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


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
        SECRET_KEY="boarding-pass-test",
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


class BoardingPassRuleTests(unittest.TestCase):
    def test_filename_and_umetrip(self):
        self.assertTrue(looks_like_boarding_pass(name="个人登机凭证.pdf"))
        self.assertTrue(looks_like_boarding_pass(text="电子登机凭证\n第 1 页/共 1 页"))
        self.assertTrue(looks_like_boarding_pass(zip_filename="航旅纵横.zip"))
        self.assertTrue(looks_like_boarding_pass(name="boarding_umetrip.pdf"))
        self.assertFalse(looks_like_boarding_pass(name="高德打车电子发票.pdf"))
        self.assertFalse(looks_like_boarding_pass(name="火车票.pdf"))

    def test_zip_type(self):
        self.assertEqual(identify_zip_type_from_filename("个人登机凭证.pdf"), "flight")
        self.assertEqual(identify_zip_type_from_filename("航旅纵横-报销.zip"), "flight")


class BoardingPassProcessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REAL_BOARDING_PASS.exists():
            raise unittest.SkipTest(f"缺少真实登机凭证样本: {REAL_BOARDING_PASS}")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        self.tmp.cleanup()

    def test_identify_real_boarding_pass(self):
        from app.services.pdf_service import identify_pdf_type

        pdf_type = identify_pdf_type(str(REAL_BOARDING_PASS), zip_filename="个人登机凭证.pdf")
        self.assertEqual(pdf_type, "flight_ticket")

    def test_two_boarding_passes_layout_on_one_page(self):
        from app.services.pdf_service import process_pdf_files
        from PyPDF2 import PdfReader

        extract_dir = Path(self.tmp.name) / "extract"
        extract_dir.mkdir()
        shutil.copy2(REAL_BOARDING_PASS, extract_dir / "个人登机凭证-去程.pdf")
        shutil.copy2(REAL_BOARDING_PASS, extract_dir / "个人登机凭证-回程.pdf")

        results, _, info = process_pdf_files(str(extract_dir), "个人登机凭证.pdf")
        self.assertEqual(len(results), 1, results)
        result = results[0]
        self.assertTrue(result.get("has_flight_ticket"))
        self.assertTrue(result.get("has_boarding_pass"))
        self.assertEqual(result.get("combined_type"), "ticket_double")
        self.assertEqual(result.get("flight_ticket_count"), 2)
        self.assertEqual(result.get("page_count"), 1)
        output_path = Path(self.app.config["OUTPUT_FOLDER"]) / result["output_file"]
        self.assertTrue(output_path.exists())
        self.assertEqual(len(PdfReader(str(output_path)).pages), 1)
        self.assertEqual(info.get("flight_tickets"), 2)

    def test_boarding_pass_pairs_with_train_ticket(self):
        from app.services.pdf_service import process_pdf_files

        extract_dir = Path(self.tmp.name) / "extract"
        extract_dir.mkdir()
        shutil.copy2(REAL_BOARDING_PASS, extract_dir / "个人登机凭证.pdf")
        (extract_dir / "G1234火车票.pdf").write_bytes(_make_pdf_bytes("中国铁路 火车票 车次 G1234 北京南 上海虹桥 票价 553.00"))

        results, _, info = process_pdf_files(str(extract_dir), "交通票.zip")
        self.assertEqual(len(results), 1, results)
        result = results[0]
        self.assertTrue(result.get("has_train_ticket"))
        self.assertTrue(result.get("has_flight_ticket"))
        self.assertTrue(result.get("has_boarding_pass"))
        self.assertEqual(result.get("combined_type"), "ticket_double")
        self.assertEqual(result.get("train_ticket_count"), 2)
        self.assertEqual(info.get("train_tickets"), 1)
        self.assertEqual(info.get("flight_tickets"), 1)


class BoardingPassUploadApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REAL_BOARDING_PASS.exists():
            raise unittest.SkipTest(f"缺少真实登机凭证样本: {REAL_BOARDING_PASS}")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_upload_two_same_named_boarding_passes(self):
        raw = REAL_BOARDING_PASS.read_bytes()
        files = [
            (io.BytesIO(raw), "个人登机凭证.pdf"),
            (io.BytesIO(raw), "个人登机凭证.pdf"),
        ]
        response = self.client.post(
            "/api/upload",
            data={"files": files},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload.get("success"))
        results = payload.get("results") or []
        self.assertEqual(len(results), 2)
        for item in results:
            self.assertTrue(item.get("has_flight_ticket"))
            self.assertTrue(item.get("has_boarding_pass"))

        from app.services.pdf_service import create_train_merged_entry

        with self.app.app_context():
            merged = create_train_merged_entry(results)
        self.assertTrue(merged.get("success"), merged)
        merged_result = merged["result"]
        self.assertEqual(merged_result.get("flight_ticket_count"), 2)
        self.assertEqual(merged_result.get("page_count"), 1)
        self.assertTrue(merged_result.get("has_boarding_pass"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
