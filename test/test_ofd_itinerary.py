#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OFD 航空运输电子客票行程单解析、转换和上传测试。"""

import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ofd_service import (  # noqa: E402
    OFDValidationError,
    parse_air_itinerary_metadata,
    prepare_ofd_for_processing,
    validate_ofd_archive,
)


SAMPLE_ENV = os.environ.get("ORDER_OFD_SAMPLE", "")
REAL_OFD = Path(SAMPLE_ENV) if SAMPLE_ENV else PROJECT_ROOT / "temp_files" / "航空电子客票行程单.ofd"


def _build_xbrl() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
 xmlns:atr="http://xbrl.mof.gov.cn/taxonomy/2021-11-30/atr">
 <atr:PassengerName>TEST PASSENGER</atr:PassengerName>
 <atr:ElectronicInvoiceAirTransportReceiptNumber>26000000000000000001</atr:ElectronicInvoiceAirTransportReceiptNumber>
 <atr:DetailInformationOfAirTicketTuple>
  <atr:DepartureStation>Hangzhou Xiaoshan</atr:DepartureStation>
  <atr:DestinationStation>Chongqing Jiangbei</atr:DestinationStation>
  <atr:Flight>CA4554</atr:Flight>
  <atr:CarrierDate>2026-08-20</atr:CarrierDate>
  <atr:DepartureTime>11:20</atr:DepartureTime>
 </atr:DetailInformationOfAirTicketTuple>
 <atr:TotalAmount>1110.00</atr:TotalAmount>
 <atr:ETicketNumber>9992562574486</atr:ETicketNumber>
 <atr:IssueDate>2026-09-08</atr:IssueDate>
</xbrli:xbrl>"""


def _write_metadata_only_ofd(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("OFD.xml", b"<?xml version='1.0'?><OFD/>")
        archive.writestr("Doc_0/Attachs/air-ticket.xml", _build_xbrl())


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
        SECRET_KEY="ofd-itinerary-test",
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


class OFDMetadataTests(unittest.TestCase):
    def test_parse_air_ticket_xbrl(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.ofd"
            _write_metadata_only_ofd(sample)
            metadata = parse_air_itinerary_metadata(str(sample))

        self.assertEqual(metadata["document_type"], "flight_ticket")
        self.assertEqual(metadata["invoice_number"], "26000000000000000001")
        self.assertEqual(metadata["ticket_number"], "9992562574486")
        self.assertEqual(metadata["amount"], 1110.00)
        self.assertEqual(metadata["flight_no"], "CA4554")
        self.assertEqual(metadata["from_station"], "HangzhouXiaoshan")
        self.assertEqual(metadata["to_station"], "ChongqingJiangbei")

    def test_reject_zip_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "unsafe.ofd"
            with zipfile.ZipFile(sample, "w") as archive:
                archive.writestr("OFD.xml", "<OFD/>")
                archive.writestr("../outside.xml", _build_xbrl())
            with self.assertRaises(OFDValidationError):
                validate_ofd_archive(str(sample))


@unittest.skipUnless(REAL_OFD.is_file(), f"缺少真实 OFD 样本: {REAL_OFD}")
class RealOFDItineraryTests(unittest.TestCase):
    def test_parse_and_convert_real_itinerary(self):
        from PyPDF2 import PdfReader

        with tempfile.TemporaryDirectory() as tmp:
            pdf_path, metadata = prepare_ofd_for_processing(
                str(REAL_OFD),
                tmp,
                original_filename=REAL_OFD.name,
            )
            reader = PdfReader(pdf_path)
            self.assertEqual(len(reader.pages), 1)
            self.assertGreater(Path(pdf_path).stat().st_size, 10000)

        self.assertEqual(metadata["invoice_number"], "26118999111069125974")
        self.assertEqual(metadata["ticket_number"], "9992562574486")
        self.assertEqual(metadata["amount"], 1110.00)
        self.assertEqual(metadata["flight_no"], "CA4554")
        self.assertEqual(metadata["from_station"], "杭州萧山")
        self.assertEqual(metadata["to_station"], "重庆江北")
        self.assertEqual(metadata["travel_date"], "2026-08-20")
        self.assertEqual(metadata["departure_time"], "11:20")

    def test_upload_real_itinerary(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = _build_test_app(tmp)
            client = app.test_client()
            payload_file = io.BytesIO(REAL_OFD.read_bytes())
            response = client.post(
                "/api/upload",
                data={"files": [(payload_file, REAL_OFD.name)]},
                content_type="multipart/form-data",
            )
            payload_file.close()

            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
            payload = response.get_json()
            self.assertTrue(payload.get("success"))
            results = payload.get("results") or []
            self.assertEqual(len(results), 1, results)
            result = results[0]
            self.assertEqual(result["order_id"], "26118999111069125974")
            self.assertTrue(result.get("has_flight_ticket"))
            self.assertEqual(result.get("combined_type"), "flight_single")
            self.assertEqual(result.get("amount"), 1110.00)
            self.assertEqual(result.get("flight_amount"), 1110.00)
            self.assertEqual(result.get("train_routes"), ["杭州萧山→重庆江北(CA4554)"])
            items = result.get("train_ticket_items") or []
            self.assertEqual(items[0].get("flight_no"), "CA4554")
            self.assertEqual(items[0].get("ticket_number"), "9992562574486")
            self.assertEqual(items[0].get("source_format"), "ofd")
            self.assertEqual(payload["current_session"]["flight_amount"], 1110.00)
            self.assertEqual(payload["current_session"]["taxi_amount"], 0)

            output = Path(app.config["OUTPUT_FOLDER"]) / result["output_file"]
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 10000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
