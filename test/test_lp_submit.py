#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lp 提交串行、超时与瞬态失败重试。"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.print_service import (  # noqa: E402
    _parse_lp_job_id,
    _lp_is_permanent_error,
    _lp_is_transient_error,
    print_pdf,
)


def _completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["lp"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


class LpHelperTests(unittest.TestCase):
    def test_parse_job_id(self):
        self.assertEqual(
            _parse_lp_job_id("request id is HP_M437_ULD-123 (1 file(s))"),
            "HP_M437_ULD-123",
        )
        self.assertEqual(_parse_lp_job_id("lp：成功"), "")

    def test_permanent_vs_transient(self):
        self.assertTrue(_lp_is_permanent_error("lp: Unknown destination"))
        self.assertTrue(_lp_is_transient_error("lp：没有那个文件或目录"))
        self.assertTrue(_lp_is_transient_error("No such file or directory"))
        self.assertFalse(_lp_is_transient_error("request id is HP_M437_ULD-1"))


class PrintPdfRetryTests(unittest.TestCase):
    def setUp(self):
        from app import create_app

        self.tmp = tempfile.TemporaryDirectory()
        tmp_dir = Path(self.tmp.name)
        self.tmp_dir = tmp_dir
        self.pdf_path = tmp_dir / "order_1_test.pdf"
        self.pdf_path.write_bytes(b"%PDF-1.4\n")
        self.app = create_app()
        self.app.config.update(TESTING=True, DATA_FOLDER=str(tmp_dir / "data"))
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        self.tmp.cleanup()

    def _print(self, media_source=None):
        return print_pdf(
            str(self.pdf_path),
            printer_name="HP_M437_ULD",
            media_source=media_source,
        )

    @patch("app.services.print_service.time.sleep")
    @patch("app.services.print_service.shutil.which", return_value="/usr/bin/lp")
    @patch("app.services.print_service.subprocess.run")
    def test_retries_fake_success_then_queues(self, mock_run, _which, mock_sleep):
        mock_run.side_effect = [
            _completed(1, stdout="lp：成功"),
            _completed(0, stdout="request id is HP_M437_ULD-88 (1 file(s))"),
        ]
        result = self._print()
        self.assertTrue(result["success"])
        self.assertEqual(result["job_id"], "HP_M437_ULD-88")
        self.assertEqual(mock_run.call_count, 2)
        self.assertTrue(mock_sleep.called)

    @patch("app.services.print_service.time.sleep")
    @patch("app.services.print_service.shutil.which", return_value="/usr/bin/lp")
    @patch("app.services.print_service.subprocess.run")
    def test_retries_missing_file_error(self, mock_run, _which, mock_sleep):
        mock_run.side_effect = [
            _completed(1, stderr="lp：没有那个文件或目录"),
            _completed(0, stdout="request id is HP_M437_ULD-9 (1 file(s))"),
        ]
        result = self._print()
        self.assertTrue(result["success"])
        self.assertEqual(mock_run.call_count, 2)

    @patch("app.services.print_service.time.sleep")
    @patch("app.services.print_service.shutil.which", return_value="/usr/bin/lp")
    @patch("app.services.print_service.subprocess.run")
    def test_does_not_retry_unknown_printer(self, mock_run, _which, mock_sleep):
        mock_run.return_value = _completed(1, stderr="lp: Unknown destination")
        result = self._print()
        self.assertFalse(result["success"])
        self.assertEqual(mock_run.call_count, 1)

    @patch("app.services.print_service.time.sleep")
    @patch("app.services.print_service.shutil.which", return_value="/usr/bin/lp")
    @patch("app.services.print_service.subprocess.run")
    def test_retries_timeout_then_succeeds(self, mock_run, _which, mock_sleep):
        mock_run.side_effect = [
            subprocess.TimeoutExpired(cmd="lp", timeout=30),
            _completed(0, stdout="request id is HP_M437_ULD-12 (1 file(s))"),
        ]
        result = self._print()
        self.assertTrue(result["success"])
        self.assertEqual(mock_run.call_count, 2)

    @patch("app.services.print_service.time.sleep")
    @patch("app.services.print_service.shutil.which", return_value="/usr/bin/lp")
    @patch("app.services.print_service.subprocess.run")
    def test_auto_uses_printer_default_without_media_source(self, mock_run, _which, mock_sleep):
        mock_run.return_value = _completed(0, stdout="request id is HP_M437_ULD-1 (1 file(s))")
        self._print(media_source="auto")
        cmd = mock_run.call_args.args[0]
        self.assertFalse(any(str(arg).startswith("media-source=") for arg in cmd))

    @patch("app.services.print_service.time.sleep")
    @patch("app.services.print_service.shutil.which", return_value="/usr/bin/lp")
    @patch("app.services.print_service.subprocess.run")
    def test_explicit_media_source_is_forwarded(self, mock_run, _which, mock_sleep):
        mock_run.return_value = _completed(0, stdout="request id is HP_M437_ULD-1 (1 file(s))")
        self._print(media_source="Upper")
        cmd = mock_run.call_args.args[0]
        self.assertIn("media-source=Upper", cmd)

    @patch("app.services.print_service.time.sleep")
    @patch("app.services.print_service.shutil.which", return_value="/usr/bin/lp")
    @patch("app.services.print_service.subprocess.run")
    def test_forces_c_locale(self, mock_run, _which, mock_sleep):
        mock_run.return_value = _completed(0, stdout="request id is HP_M437_ULD-1 (1 file(s))")
        self._print()
        env = mock_run.call_args.kwargs["env"]
        self.assertEqual(env["LC_ALL"], "C")
        self.assertEqual(env["LANG"], "C")


if __name__ == "__main__":
    unittest.main()
