#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""已打印过的网约车 ZIP 再拖进来：打印件可复用，页面金额仍要计入。"""

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _make_pdf_bytes(text="electronic invoice"):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def _zip_writestr(zf, name, data):
    info = zipfile.ZipInfo(name)
    info.date_time = (2026, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)


def _taxi_zip_bytes(order_label, amount, extra=""):
    raw = io.BytesIO()
    prefix = f"【{order_label}-{amount:.2f}元-1个行程】"
    with zipfile.ZipFile(raw, "w") as zf:
        _zip_writestr(zf, prefix + "高德打车电子发票.pdf", _make_pdf_bytes(f"invoice {extra}"))
        _zip_writestr(zf, prefix + "高德打车电子行程单.pdf", _make_pdf_bytes(f"itinerary {extra}"))
        _zip_writestr(
            zf,
            prefix + "高德打车电子发票.xml",
            f"<Invoice><TotalTax-includedAmount>{amount:.2f}</TotalTax-includedAmount></Invoice>",
        )
    return raw.getvalue()


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
        SECRET_KEY="reuse-amount-test",
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


class ReusedTaxiUploadAmountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def _upload(self, named_zips):
        files = []
        buffers = []
        for zip_name, content in named_zips:
            raw = io.BytesIO(content)
            buffers.append(raw)
            files.append((raw, zip_name))
        response = self.client.post(
            "/api/upload",
            data={"files": files},
            content_type="multipart/form-data",
        )
        for buf in buffers:
            buf.close()
        return response

    def test_reupload_same_zip_still_counts_page_amount(self):
        zip_bytes = _taxi_zip_bytes("享道出行", 78.17, extra="a")
        first = self._upload([("高德打车电子发票 (2).zip", zip_bytes)])
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))
        first_payload = first.get_json()
        self.assertEqual(first_payload["current_session"]["taxi_amount"], 78.17)
        self.assertEqual(first_payload["current_session"]["total_amount"], 78.17)
        self.assertEqual(first_payload["new_results_count"], 1)
        first_global = first_payload["global_stats"]["total_amount"]
        first_output = first_payload["results"][0].get("output_file")

        second = self._upload([("高德打车电子发票 (2).zip", zip_bytes)])
        self.assertEqual(second.status_code, 200, second.get_data(as_text=True))
        second_payload = second.get_json()
        self.assertGreaterEqual(second_payload.get("reused_files", 0), 1)
        self.assertEqual(second_payload["new_results_count"], 0)
        self.assertEqual(second_payload["current_session"]["taxi_amount"], 78.17)
        self.assertEqual(second_payload["current_session"]["total_amount"], 78.17)
        self.assertEqual(second_payload["global_stats"]["total_amount"], first_global)

        results = second_payload.get("results") or []
        self.assertTrue(results)
        self.assertEqual(results[0].get("amount"), 78.17)
        self.assertEqual(results[0].get("output_file"), first_output)

    def test_reupload_with_new_file_sums_both(self):
        invoice_two = _taxi_zip_bytes("享道出行", 78.17, extra="a")
        invoice_four = _taxi_zip_bytes("腾飞出行", 18.28, extra="b")
        first = self._upload([("高德打车电子发票 (2).zip", invoice_two)])
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))
        first_global = first.get_json()["global_stats"]["total_amount"]

        mixed = self._upload([
            ("高德打车电子发票 (2).zip", invoice_two),
            ("高德打车电子发票 (4).zip", invoice_four),
        ])
        self.assertEqual(mixed.status_code, 200, mixed.get_data(as_text=True))
        payload = mixed.get_json()
        self.assertGreaterEqual(payload.get("reused_files", 0), 1)
        self.assertEqual(payload["new_results_count"], 1)
        self.assertAlmostEqual(payload["current_session"]["taxi_amount"], 96.45, places=2)
        self.assertAlmostEqual(payload["current_session"]["total_amount"], 96.45, places=2)
        self.assertAlmostEqual(
            payload["global_stats"]["total_amount"],
            first_global + 18.28,
            places=2,
        )


if __name__ == "__main__":
    unittest.main()
