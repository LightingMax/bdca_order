#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app


class PrintMergedRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    @patch("app.routes.print_pdf")
    @patch("app.services.pdf_service.create_download_collection")
    @patch("app.services.pdf_service.create_train_merged_entry")
    def test_multiple_flights_are_replaced_by_one_transport_merge(
        self, mock_train_merge, mock_collection, mock_print
    ):
        mock_train_merge.return_value = {
            "success": True,
            "file_path": "/tmp/train_merged.pdf",
            "result": {
                "output_file": "train_merged.pdf",
                "is_train_merged_entry": True,
                "has_transport_ticket": True,
                "combined_type": "ticket_merged_all",
            },
        }
        mock_collection.return_value = {
            "success": True,
            "filename": "all.pdf",
            "file_path": "/tmp/all.pdf",
        }
        mock_print.return_value = {
            "success": True,
            "printer": "HP_M437_ULD",
            "job_id": "HP_M437_ULD-1",
            "queue_confirmed": True,
            "returncode": 0,
            "message": "queued",
        }

        response = self.client.post("/api/print-merged", json={
            "processed_files": [
                {"output_file": "receipt.pdf", "combined_type": "rideshare"},
                {"output_file": "flight_a.pdf", "has_flight_ticket": True},
                {"output_file": "flight_b.pdf", "has_transport_ticket": True},
            ],
            "collection_name": "智能打印合集",
        })

        self.assertEqual(response.status_code, 200)
        mock_train_merge.assert_called_once()
        files_for_collection = mock_collection.call_args.args[0]
        self.assertEqual(
            [item["output_file"] for item in files_for_collection],
            ["receipt.pdf", "train_merged.pdf"],
        )
        self.assertEqual(response.get_json()["file_count"], 2)
        mock_print.assert_called_once_with("/tmp/all.pdf", processing_log=unittest.mock.ANY)


if __name__ == "__main__":
    unittest.main()
