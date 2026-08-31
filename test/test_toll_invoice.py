#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""过路费发票识别、处理与金额汇总测试。

覆盖：
1. 票根包文件名规则（用户真实命名）
2. 正向/负向关键词，避免把网约车发票里的过路费明细当成独立过路费
3. 智能处理 /api/upload 接口
4. 求和与分类统计把过路费计入总金额，但不并入网约车
"""

import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pdf_service import (  # noqa: E402
    build_toll_order_id,
    extract_toll_invoice_amount,
    identify_zip_type_from_filename,
    looks_like_toll_invoice,
    parse_toll_invoice_source,
)

SAMPLE_ZIPS = [
    ("浙ADA2734[渐变绿]+202608291849+21.00元.zip", "浙ADA2734", "渐变绿", "202608291849", 21.00),
    ("浙ADN4891[渐变绿]+202608201011+29.00元.zip", "浙ADN4891", "渐变绿", "202608201011", 29.00),
]


def _make_pdf_bytes(text="electronic invoice"):
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def _write_zip(zip_path, inner_name="发票.pdf", pdf_text="electronic invoice", xml_amount=None):
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(inner_name, _make_pdf_bytes(pdf_text))
        if xml_amount is not None:
            zf.writestr(
                "invoice.xml",
                f"<Invoice><TotalTax-includedAmount>{xml_amount:.2f}</TotalTax-includedAmount></Invoice>",
            )
    return zip_path


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
        SECRET_KEY="toll-invoice-test",
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


class TollInvoiceRuleTests(unittest.TestCase):
    def test_parse_piaogen_zip_names(self):
        for filename, plate, color, when, amount in SAMPLE_ZIPS:
            with self.subTest(filename=filename):
                meta = parse_toll_invoice_source(filename)
                self.assertIsNotNone(meta)
                self.assertEqual(meta["plate"], plate)
                self.assertEqual(meta["color"], color)
                self.assertEqual(meta["when"], when)
                self.assertEqual(meta["amount"], amount)

    def test_other_plate_colors_and_provinces(self):
        cases = [
            "京A12345[蓝色]+202601011200+15.50元.zip",
            "粤B88888[黄色]+202512312359+8.00元",
            "沪C00001[白色]+202608150800+100.25元.pdf",
        ]
        for name in cases:
            self.assertIsNotNone(parse_toll_invoice_source(name), name)

    def test_zip_type_is_toll_for_piaogen_names(self):
        for filename, *_ in SAMPLE_ZIPS:
            self.assertEqual(identify_zip_type_from_filename(filename), "toll")
        self.assertEqual(identify_zip_type_from_filename("通行费发票.zip"), "toll")
        self.assertEqual(identify_zip_type_from_filename("过路费-报销.zip"), "toll")

    def test_zip_type_does_not_steal_taxi_or_hotel(self):
        self.assertEqual(identify_zip_type_from_filename("【阳光出行-32.13元-3个行程】高德打车电子发票.zip"), "taxi")
        self.assertEqual(identify_zip_type_from_filename("华住酒店结账单.zip"), "hotel")

    def test_positive_keywords_without_negatives(self):
        self.assertTrue(looks_like_toll_invoice(name="收费公路通行费电子发票.pdf"))
        self.assertTrue(looks_like_toll_invoice(text="货物名称：*经营租赁*通行费"))
        self.assertTrue(looks_like_toll_invoice(zip_filename=SAMPLE_ZIPS[0][0], name="发票.pdf"))

    def test_taxi_invoice_surcharge_is_not_toll(self):
        self.assertFalse(
            looks_like_toll_invoice(
                name="【及时用车-53.21元-2个行程】高德打车电子发票.pdf",
                text="价税合计 53.21 其中过路费 5.00",
            )
        )
        self.assertFalse(
            looks_like_toll_invoice(
                name="发票.pdf",
                text="滴滴出行 客运服务费 过路费 12.00",
                zip_filename="滴滴出行电子发票.zip",
            )
        )
        self.assertFalse(looks_like_toll_invoice(name="高德打车电子行程单.pdf", text="过路费"))

    def test_amount_prefers_piaogen_filename(self):
        amount = extract_toll_invoice_amount(
            "发票.pdf",
            zip_filename=SAMPLE_ZIPS[0][0],
            xml_path=None,
        )
        self.assertEqual(amount, 21.00)

    def test_order_id_is_stable_and_unique(self):
        first = build_toll_order_id("发票.pdf", SAMPLE_ZIPS[0][0], 21)
        second = build_toll_order_id("发票.pdf", SAMPLE_ZIPS[1][0], 29)
        self.assertEqual(first, "过路费-浙ADA2734-202608291849-21.00元")
        self.assertEqual(second, "过路费-浙ADN4891-202608201011-29.00元")
        self.assertNotEqual(first, second)


class TollInvoiceAmountAggregationTests(unittest.TestCase):
    def test_toll_is_separate_and_included_in_total(self):
        from app.routes import _aggregate_result_amounts, _extract_result_amounts

        taxi = {"order_id": "阳光出行-32.13元-1个行程", "amount": 32.13, "has_invoice": True, "has_itinerary": True}
        hotel = {"order_id": "hotel_abc", "amount": 200.00, "has_hotel_bill": True}
        train = {"order_id": "G123", "amount": 50.00, "has_train_ticket": True, "train_amount": 50.00}
        toll_a = {
            "order_id": "过路费-浙ADA2734-202608291849-21.00元",
            "amount": 21.00,
            "has_toll_invoice": True,
            "combined_type": "toll_invoice",
            "toll_amount": 21.00,
        }
        toll_b = {
            "order_id": "过路费-浙ADN4891-202608201011-29.00元",
            "amount": 29.00,
            "has_toll_invoice": True,
            "combined_type": "toll_invoice",
            "toll_amount": 29.00,
        }

        self.assertEqual(_extract_result_amounts(toll_a), (0.0, 0.0, 0.0, 0.0, 21.00))
        stats = _aggregate_result_amounts([taxi, hotel, train, toll_a, toll_b])
        self.assertEqual(stats["taxi_amount"], 32.13)
        self.assertEqual(stats["hotel_amount"], 200.00)
        self.assertEqual(stats["train_amount"], 50.00)
        self.assertEqual(stats["toll_amount"], 50.00)
        self.assertEqual(stats["total_amount"], 332.13)

    def test_duplicate_toll_results_are_deduped(self):
        from app.routes import _aggregate_result_amounts

        item = {
            "order_id": "过路费-浙ADA2734-202608291849-21.00元",
            "amount": 21.00,
            "has_toll_invoice": True,
            "combined_type": "toll_invoice",
        }
        stats = _aggregate_result_amounts([item, dict(item)])
        self.assertEqual(stats["toll_amount"], 21.00)
        self.assertEqual(stats["order_count"], 1)

    def test_merged_double_counts_once(self):
        from app.routes import _aggregate_result_amounts, _extract_result_amounts

        merged = {
            "order_id": "过路费-浙ADA2734+浙ADN4891-50.00元",
            "amount": 50.00,
            "has_toll_invoice": True,
            "is_toll_merged": True,
            "combined_type": "toll_double",
            "toll_amount": 50.00,
        }
        self.assertEqual(_extract_result_amounts(merged), (0.0, 0.0, 0.0, 0.0, 50.00))
        stats = _aggregate_result_amounts([merged])
        self.assertEqual(stats["toll_amount"], 50.00)
        self.assertEqual(stats["total_amount"], 50.00)
        self.assertEqual(stats["order_count"], 1)


class TollInvoiceProcessingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        self.tmp.cleanup()

    def test_identify_pdf_type_uses_zip_name(self):
        from app.services.pdf_service import identify_pdf_type

        pdf_path = Path(self.tmp.name) / "发票.pdf"
        pdf_path.write_bytes(_make_pdf_bytes("invoice"))
        pdf_type = identify_pdf_type(str(pdf_path), zip_filename=SAMPLE_ZIPS[0][0])
        self.assertEqual(pdf_type, "toll_invoice")

    def test_taxi_invoice_filename_with_trip_count_stays_invoice(self):
        from app.services.pdf_service import identify_pdf_type

        pdf_path = Path(self.tmp.name) / "【及时用车-53.21元-2个行程】高德打车电子发票.pdf"
        pdf_path.write_bytes(_make_pdf_bytes("gaode taxi invoice"))
        pdf_type = identify_pdf_type(str(pdf_path), zip_filename="高德打车电子发票.zip")
        self.assertEqual(pdf_type, "invoice")

    def test_process_pdf_files_prints_and_counts_amount(self):
        from app.services.pdf_service import process_pdf_files

        extract_dir = Path(self.tmp.name) / "extracted"
        zip_name = SAMPLE_ZIPS[0][0]
        zip_path = _write_zip(Path(self.tmp.name) / zip_name, inner_name="发票.pdf")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        results, warnings, info = process_pdf_files(str(extract_dir), zip_name)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result["has_toll_invoice"])
        self.assertEqual(result["combined_type"], "toll_invoice")
        self.assertEqual(result["amount"], 21.00)
        self.assertTrue(result["output_file"])
        output_path = Path(self.app.config["OUTPUT_FOLDER"]) / result["output_file"]
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 1000)
        self.assertEqual(info["toll_amount"], 21.00)
        self.assertEqual(info["taxi_amount"], 0)
        self.assertEqual(info["total_amount"], 21.00)
        self.assertEqual(info["toll_orders"], 1)

    def test_two_toll_zips_sum_into_total(self):
        from app.services.pdf_service import process_pdf_files

        all_results = []
        all_info = []
        for filename, *_rest, amount in SAMPLE_ZIPS:
            extract_dir = Path(self.tmp.name) / Path(filename).stem
            zip_path = _write_zip(Path(self.tmp.name) / filename)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
            results, _, info = process_pdf_files(str(extract_dir), filename)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["amount"], amount)
            all_results.extend(results)
            all_info.append(info)

        from app.routes import _aggregate_result_amounts

        stats = _aggregate_result_amounts(all_results)
        self.assertEqual(stats["toll_amount"], 50.00)
        self.assertEqual(stats["total_amount"], 50.00)
        self.assertEqual(stats["taxi_amount"], 0)


class TollInvoiceUploadApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def _upload_zips(self, zip_specs):
        files = []
        buffers = []
        for zip_name, amount in zip_specs:
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, "w") as zf:
                zf.writestr("发票.pdf", _make_pdf_bytes("invoice"))
            raw.seek(0)
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

    def test_upload_api_accepts_two_piaogen_zips(self):
        response = self._upload_zips([
            (SAMPLE_ZIPS[0][0], 21.00),
            (SAMPLE_ZIPS[1][0], 29.00),
        ])
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("new_results_count"), 1)
        self.assertEqual(payload["current_session"]["toll_amount"], 50.00)
        self.assertEqual(payload["current_session"]["total_amount"], 50.00)
        self.assertEqual(payload["current_session"]["taxi_amount"], 0)
        self.assertEqual(payload["classification_info"]["toll_amount"], 50.00)
        self.assertEqual(payload["total_amount"], 50.00)

        results = payload.get("results") or []
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result.get("has_toll_invoice"))
        self.assertTrue(result.get("output_file"))
        self.assertEqual(result.get("combined_type"), "toll_double")
        self.assertEqual(result.get("amount"), 50.00)
        self.assertEqual(result.get("page_count"), 1)
        self.assertEqual(result.get("toll_invoice_count"), 2)

    def test_upload_two_zips_one_at_a_time_merges_in_session(self):
        first = self._upload_zips([(SAMPLE_ZIPS[0][0], 21.00)])
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))
        first_payload = first.get_json()
        self.assertEqual(len(first_payload.get("results") or []), 1)
        self.assertEqual(first_payload["results"][0]["combined_type"], "toll_invoice")
        self.assertEqual(first_payload["current_session"]["toll_amount"], 21.00)

        second = self._upload_zips([(SAMPLE_ZIPS[1][0], 29.00)])
        self.assertEqual(second.status_code, 200, second.get_data(as_text=True))
        second_payload = second.get_json()
        results = second_payload.get("results") or []
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("combined_type"), "toll_double")
        self.assertEqual(results[0].get("amount"), 50.00)
        self.assertEqual(results[0].get("page_count"), 1)
        replaced = set(results[0].get("replaced_order_ids") or [])
        self.assertEqual(len(replaced), 2)
        self.assertEqual(second_payload["current_session"]["toll_amount"], 29.00)

    def test_step_by_step_after_two_at_once_returns_one_double(self):
        """先两张一起上传，再逐步各传一次，接口仍只返回一份双拼。"""
        together = self._upload_zips([
            (SAMPLE_ZIPS[0][0], 21.00),
            (SAMPLE_ZIPS[1][0], 29.00),
        ])
        self.assertEqual(together.status_code, 200, together.get_data(as_text=True))
        first_double = (together.get_json().get("results") or [{}])[0]
        self.assertEqual(first_double.get("combined_type"), "toll_double")

        first = self._upload_zips([(SAMPLE_ZIPS[0][0], 21.00)])
        self.assertEqual(first.status_code, 200, first.get_data(as_text=True))

        second = self._upload_zips([(SAMPLE_ZIPS[1][0], 29.00)])
        self.assertEqual(second.status_code, 200, second.get_data(as_text=True))
        results = second.get_json().get("results") or []
        doubles = [item for item in results if item.get("combined_type") == "toll_double"]
        singles = [item for item in results if item.get("combined_type") == "toll_invoice"]
        self.assertEqual(len(doubles), 1, results)
        self.assertEqual(len(singles), 0, results)
        self.assertEqual(doubles[0].get("amount"), 50.00)
        self.assertEqual(doubles[0].get("page_count"), 1)
        self.assertEqual(len(doubles[0].get("replaced_order_ids") or []), 2)
        self.assertNotEqual(doubles[0].get("output_file"), first_double.get("output_file"))

    def test_three_toll_zips_become_double_plus_single(self):
        third = "沪C00001[白色]+202608150800+10.00元.zip"
        response = self._upload_zips([
            (SAMPLE_ZIPS[0][0], 21.00),
            (SAMPLE_ZIPS[1][0], 29.00),
            (third, 10.00),
        ])
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        results = payload.get("results") or []
        self.assertEqual(len(results), 2)
        types = sorted(item.get("combined_type") for item in results)
        self.assertEqual(types, ["toll_double", "toll_invoice"])
        self.assertEqual(payload["current_session"]["toll_amount"], 60.00)
        self.assertEqual(payload["current_session"]["total_amount"], 60.00)
        page_counts = sorted(int(item.get("page_count") or 0) for item in results)
        self.assertEqual(page_counts, [1, 1])


class TollInvoiceRealFixtureTests(unittest.TestCase):
    """用 temp_files 里的真实票根包回归，文件不存在则跳过。"""

    REAL_ZIPS = [
        (PROJECT_ROOT / "temp_files" / SAMPLE_ZIPS[0][0], 21.00, "浙ADA2734"),
        (PROJECT_ROOT / "temp_files" / SAMPLE_ZIPS[1][0], 29.00, "浙ADN4891"),
    ]

    @classmethod
    def setUpClass(cls):
        missing = [str(path) for path, *_ in cls.REAL_ZIPS if not path.exists()]
        if missing:
            raise unittest.SkipTest("缺少真实过路费样本: " + ", ".join(missing))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = _build_test_app(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_upload_real_piaogen_zips_from_temp_files(self):
        files = []
        buffers = []
        for path, _amount, _plate in self.REAL_ZIPS:
            buf = io.BytesIO(path.read_bytes())
            buffers.append(buf)
            files.append((buf, path.name))

        response = self.client.post(
            "/api/upload",
            data={"files": files},
            content_type="multipart/form-data",
        )
        for buf in buffers:
            buf.close()

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("new_results_count"), 1)
        self.assertEqual(payload["current_session"]["toll_amount"], 50.00)
        self.assertEqual(payload["current_session"]["total_amount"], 50.00)
        self.assertEqual(payload["current_session"]["taxi_amount"], 0)

        results = payload.get("results") or []
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertTrue(result.get("has_toll_invoice"))
        self.assertEqual(result.get("combined_type"), "toll_double")
        self.assertEqual(result.get("amount"), 50.00)
        self.assertEqual(result.get("page_count"), 1)
        self.assertEqual(result.get("toll_invoice_count"), 2)
        self.assertIn("浙ADA2734", result.get("toll_plate") or "")
        self.assertIn("浙ADN4891", result.get("toll_plate") or "")
        output_path = Path(self.app.config["OUTPUT_FOLDER"]) / result["output_file"]
        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 50_000)
        from PyPDF2 import PdfReader
        self.assertEqual(len(PdfReader(str(output_path)).pages), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
