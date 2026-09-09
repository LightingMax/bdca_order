"""easyofd 隔离工作进程；由 ofd_service 调用，不直接处理上传请求。"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import types
from pathlib import Path


def _register_chinese_font(font_path: str) -> None:
    from reportlab.pdfbase import pdfmetrics

    if font_path:
        from reportlab.pdfbase.ttfonts import TTFont

        try:
            try:
                font = TTFont("宋体", font_path, subfontIndex=0)
            except TypeError:
                font = TTFont("宋体", font_path)
            pdfmetrics.registerFont(font)
            return
        except Exception:
            pass

    # 无系统 TrueType 中文字体时使用 ReportLab 自带简体中文 CID 字体。
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    font = UnicodeCIDFont("STSong-Light")
    font.name = font.fontName = "宋体"
    pdfmetrics.registerFont(font)


def convert(source: Path, destination: Path, font_path: str = "") -> None:
    # easyofd 只在未启用的字形绘制分支引用 renderPM。旧版 ReportLab 在
    # Python 3.12 下加载其二进制扩展会失败，因此在本工作进程中提供空模块。
    sys.modules.setdefault(
        "reportlab.graphics.renderPM",
        types.ModuleType("reportlab.graphics.renderPM"),
    )
    try:
        from loguru import logger as loguru_logger

        loguru_logger.disable("easyofd")
    except Exception:
        pass

    _register_chinese_font(font_path)
    from easyofd import OFD
    from easyofd.draw.font_tools import FontTool

    # easyofd 默认遍历所有系统字体但没有注册它们；指定已注册字体既正确又更快。
    FontTool.get_installed_fonts = lambda self: ["宋体"]
    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
        document = OFD()
        document.read(str(source), fmt="path")
        pdf_bytes = document.to_pdf()
    if (
        not isinstance(pdf_bytes, (bytes, bytearray))
        or not pdf_bytes.startswith(b"%PDF-")
        or len(pdf_bytes) < 5000
    ):
        raise RuntimeError("转换器未生成 PDF")
    destination.write_bytes(pdf_bytes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--font", default="")
    args = parser.parse_args()
    try:
        convert(Path(args.source), Path(args.destination), args.font)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
