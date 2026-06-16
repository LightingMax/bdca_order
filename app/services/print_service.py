import os
import re
import shutil
import subprocess
import uuid
from flask import current_app
from app.config import Config

WORD_EXTENSIONS = {".doc", ".docx"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _log_step(processing_log, message, level="info"):
    """记录处理步骤，供接口返回给前端展示。"""
    current_app.logger.info(message)
    if processing_log is not None:
        processing_log.append({"message": message, "level": level})


def describe_raw_print_pipeline(file_path):
    """根据文件类型描述原始打印将经历的步骤，用于上传后提示用户。"""
    ext = os.path.splitext(str(file_path or ""))[1].lower()
    if ext in IMAGE_EXTENSIONS:
        label = ext.lstrip(".").upper()
        return f"打印时将：检测图片（{label}）→ 转换为 A4 标准 PDF → 提交打印机队列"
    if ext in WORD_EXTENSIONS:
        return "打印时将：检测 Word 文档 → LibreOffice 转 PDF → 直接提交打印机队列"
    if ext == ".pdf":
        return "打印时将：检测 PDF → 自动判断直打或适配打印 → 提交打印机队列"
    return "打印时将：准备文件 → 提交打印机队列"


_RASTERIZE_REASON_LABELS = {
    "cropbox": "页面可见区域与纸张尺寸不一致（电子发票常见，直打可能裁切或留白异常）",
    "transport_ticket": "交通票据（火车票/机票，直打可能丢字）",
    "gbk_font": "含 GBK 嵌入式字体（Docker/CUPS 直打可能缺字）",
}


def _pdf_has_gbk_like_fonts(pdf_path):
    """检测 PDF 是否嵌入 GBK 类字体，这类文件直打时容易缺字。"""
    try:
        import fitz

        doc = fitz.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            for font_info in page.get_fonts(full=True):
                encoding = str(font_info[5] or "") if len(font_info) > 5 else ""
                basefont = str(font_info[3] or "") if len(font_info) > 3 else ""
                blob = f"{encoding} {basefont}".upper()
                if any(marker in blob for marker in ("GBK", "GB-EUC", "EUC-H", "GBPC")):
                    doc.close()
                    return True
        doc.close()
    except Exception as e:
        current_app.logger.debug(f"GBK字体检测跳过: {pdf_path}, err={e}")
    return False


def _assess_raw_pdf_print_strategy(pdf_path):
    """判断原始 PDF 应直打还是栅格化后打印。"""
    from app.services.pdf_service import _should_render_invoice_with_cropbox, identify_pdf_type

    reasons = []
    use_cropbox = False

    if _should_render_invoice_with_cropbox(pdf_path):
        reasons.append("cropbox")
        use_cropbox = True

    pdf_type = identify_pdf_type(pdf_path)
    if pdf_type in ("train_ticket", "flight_ticket"):
        reasons.append("transport_ticket")

    if _pdf_has_gbk_like_fonts(pdf_path):
        reasons.append("gbk_font")

    if reasons:
        return "rasterize", reasons, use_cropbox
    return "direct", [], False


def _count_pdf_pages(pdf_path):
    try:
        import fitz

        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return max(1, count)
    except Exception:
        try:
            from PyPDF2 import PdfReader

            return max(1, len(PdfReader(pdf_path).pages))
        except Exception:
            return 1

def get_available_printers():
    """通过 CUPS 客户端命令获取可用打印机列表。"""
    logger = current_app.logger
    logger.info("正在通过 lpstat 获取可用打印机列表")

    try:
        if shutil.which("lpstat") is None:
            logger.error("系统未找到 lpstat 命令，请安装 cups-client")
            return []

        result = subprocess.run(
            ["lpstat", "-p"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"lpstat 执行失败: {result.stderr.strip()}")
            return []

        printers = []
        pattern = re.compile(r"^printer\s+(\S+)\s", re.IGNORECASE)
        for line in result.stdout.splitlines():
            match = pattern.match(line.strip())
            if match:
                printers.append(match.group(1))

        logger.info(f"通过 CUPS 找到 {len(printers)} 个打印机")
        return printers
    except Exception as e:
        logger.error(f"获取打印机列表出错: {str(e)}", exc_info=True)
        return []


def _lp_output_indicates_success(output):
    """识别 lp 在不同语言环境下的成功输出，避免非零返回码误判。"""
    normalized = (output or "").strip().lower()
    if not normalized:
        return False

    success_markers = [
        "request id is",
        "successful",
        "success",
        "submitted",
        "成功",
    ]
    failure_markers = [
        "not found",
        "no such",
        "unable",
        "failed",
        "failure",
        "error",
        "失败",
        "错误",
        "找不到",
        "无法",
    ]

    return any(marker in normalized for marker in success_markers) and not any(
        marker in normalized for marker in failure_markers
    )


def _convert_word_to_pdf(file_path):
    """将 Word 文档转换为 PDF，供 CUPS 稳定打印。"""
    logger = current_app.logger
    converter = shutil.which("libreoffice") or shutil.which("soffice")
    if converter is None:
        raise RuntimeError("系统未安装 LibreOffice，无法打印 Word 文档（.doc/.docx）")

    output_dir = os.path.join(
        current_app.config["TEMP_FOLDER"],
        "raw_print_converted",
        uuid.uuid4().hex[:8],
    )
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        converter,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        output_dir,
        file_path,
    ]
    logger.info(f"转换Word文档为PDF: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        detail = "\n".join(part for part in [stdout, stderr] if part).strip() or "未知错误"
        raise RuntimeError(f"Word文档转换PDF失败: {detail}")

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    converted_path = os.path.join(output_dir, f"{base_name}.pdf")
    if not os.path.exists(converted_path):
        candidates = [
            os.path.join(output_dir, name)
            for name in os.listdir(output_dir)
            if name.lower().endswith(".pdf")
        ]
        if candidates:
            converted_path = max(candidates, key=os.path.getmtime)

    if not os.path.exists(converted_path):
        detail = "\n".join(part for part in [stdout, stderr] if part).strip()
        raise RuntimeError(f"Word文档转换PDF后未找到输出文件: {detail}")

    logger.info(f"Word文档已转换为PDF: {converted_path}")
    return converted_path


def _save_images_on_a4_pdf(images, base_name, dpi=220):
    """把图片按比例放进A4页面并保存为PDF。"""
    from PIL import Image

    a4_width = int(8.27 * dpi)
    a4_height = int(11.69 * dpi)
    pages = []

    for image in images:
        image = image.convert("RGB")
        scale = min(1.0, a4_width / image.width, a4_height / image.height)
        if scale < 1.0:
            image = image.resize(
                (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                Image.Resampling.LANCZOS,
            )

        canvas = Image.new("RGB", (a4_width, a4_height), "white")
        x = (a4_width - image.width) // 2
        y = (a4_height - image.height) // 2
        canvas.paste(image, (x, y))
        pages.append(canvas)

    output_dir = os.path.join(current_app.config["TEMP_FOLDER"], "raw_print_a4")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{base_name}_on_a4_{uuid.uuid4().hex[:8]}.pdf")
    pages[0].save(
        output_path,
        "PDF",
        resolution=float(dpi),
        save_all=len(pages) > 1,
        append_images=pages[1:],
    )
    return output_path


def _convert_image_to_pdf(image_path, dpi=220):
    """将图片放到A4页面上保存为PDF，避免依赖CUPS图片过滤器。"""
    logger = current_app.logger
    from PIL import Image

    with Image.open(image_path) as image:
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = _save_images_on_a4_pdf([image], base_name, dpi=dpi)

    logger.info(f"图片已转换为A4 PDF: {output_path}")
    return output_path


def prepare_raw_preview_pdf(file_path):
    """为原始文件预览准备可直接打开的PDF；Word文档会在这里转换一次并复用。"""
    ext = os.path.splitext(str(file_path))[1].lower()
    if ext in WORD_EXTENSIONS:
        return _convert_word_to_pdf(file_path)
    return file_path


def prepare_raw_pdf_for_a4_print(pdf_path, dpi=220, processing_log=None):
    """准备原始打印文件；图片转 A4 PDF，Word 转 PDF，PDF 按特征直打或栅格化适配。"""
    basename = os.path.basename(str(pdf_path))
    ext = os.path.splitext(str(pdf_path))[1].lower()
    _log_step(processing_log, f"开始准备打印文件：{basename}")

    if ext in WORD_EXTENSIONS:
        _log_step(processing_log, "检测到 Word 文档，正在使用 LibreOffice 转换为 PDF...")
        pdf_path = _convert_word_to_pdf(pdf_path)
        ext = ".pdf"
        _log_step(processing_log, "Word 文档已转换为 PDF，将直接提交打印")

    if ext in IMAGE_EXTENSIONS:
        image_label = ext.lstrip(".").upper()
        _log_step(processing_log, f"检测到图片文件（{image_label}），正在转换为 A4 标准 PDF...")
        output_path = _convert_image_to_pdf(pdf_path, dpi=dpi)
        _log_step(processing_log, "图片已居中适配到 A4 页面并生成 PDF")
        return output_path

    if ext == ".pdf":
        page_count = _count_pdf_pages(pdf_path)
        strategy, reasons, use_cropbox = _assess_raw_pdf_print_strategy(pdf_path)
        if strategy == "direct":
            _log_step(
                processing_log,
                f"检测到 PDF 文件（共 {page_count} 页），内容正常，将直接提交打印机打印",
            )
            return pdf_path

        reason_text = "；".join(_RASTERIZE_REASON_LABELS[r] for r in reasons if r in _RASTERIZE_REASON_LABELS)
        _log_step(
            processing_log,
            f"检测到 PDF 文件（共 {page_count} 页）需要适配打印：{reason_text}",
            "warning",
        )
        _log_step(processing_log, "正在使用 PyMuPDF 渲染并适配到 A4 页面（请稍候）...")

        try:
            from app.services.pdf_service import _render_pdf_pages_to_pil

            images = _render_pdf_pages_to_pil(pdf_path, dpi=dpi, use_cropbox=use_cropbox)
            if not images:
                _log_step(processing_log, "渲染结果为空，回退为直接打印原 PDF", "warning")
                return pdf_path

            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_path = _save_images_on_a4_pdf(images, base_name, dpi=dpi)
            current_app.logger.info(f"原始PDF已按特殊适配放置到A4页面: {output_path}")
            _log_step(processing_log, f"PDF 已适配到 A4 页面（共 {len(images)} 页）")
            return output_path
        except Exception as e:
            current_app.logger.warning(f"原始PDF特殊适配失败，将直接打印原文件: {e}")
            _log_step(processing_log, f"适配失败，回退为直接打印原 PDF：{e}", "warning")
            return pdf_path

    _log_step(processing_log, f"文件类型 {ext or '未知'} 将按原文件提交打印", "warning")
    return pdf_path


def print_pdf(pdf_path, printer_name=None, copies=1, media_source=None, processing_log=None):
    """通过 lp 命令提交 PDF 打印任务。"""
    logger = current_app.logger
    logger.info(f"开始打印PDF文件: {pdf_path}")

    if not os.path.exists(pdf_path):
        logger.error(f"找不到文件: {pdf_path}")
        raise FileNotFoundError(f"找不到文件: {pdf_path}")

    try:
        if not printer_name:
            printer_name = Config.DEFAULT_PRINTER_NAME
            logger.debug(f"使用默认打印机: {printer_name}")
        if not printer_name:
            msg = "未配置 DEFAULT_PRINTER_NAME，请在项目根目录 .env 中设置与 CUPS 完全一致的队列名"
            logger.error(msg)
            raise ValueError(msg)

        if shutil.which("lp") is None:
            error_msg = "系统未找到 lp 命令，请安装 cups-client"
            logger.error(error_msg)
            _log_step(processing_log, error_msg, "error")
            return {"success": False, "message": error_msg, "queue_confirmed": False}

        _log_step(processing_log, f"正在提交打印任务到打印机「{printer_name}」...")

        copies_value = str(max(1, int(copies)))
        tray = (media_source or os.environ.get("DEFAULT_MEDIA_SOURCE") or "auto").strip()

        cmd = ["lp", "-d", printer_name, "-n", copies_value]
        if tray:
            cmd.extend(["-o", f"media-source={tray}"])
        cmd.append(pdf_path)

        logger.info(f"执行打印命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        combined_output = "\n".join(part for part in [stdout, stderr] if part).strip()
        output_indicates_success = _lp_output_indicates_success(combined_output)

        if result.returncode != 0 and not output_indicates_success:
            err = combined_output or "未知错误"
            logger.error(f"lp 提交失败: {err}")
            _log_step(processing_log, f"打印机队列提交失败：{err}", "error")
            return {
                "success": False,
                "message": f"lp 提交失败: {err}",
                "queue_confirmed": False,
                "returncode": result.returncode,
            }

        # 常见输出: request id is HP_M437_ULD-123 (1 file(s))
        output = combined_output
        job_id = ""
        match = re.search(r"request id is\s+(\S+)", output, re.IGNORECASE)
        if match:
            job_id = match.group(1)

        queue_confirmed = result.returncode == 0 or bool(job_id)
        if result.returncode != 0:
            err = combined_output or "未知错误"
            logger.warning(
                f"lp 返回码非0，任务可能未真正入队: returncode={result.returncode}, output={combined_output}"
            )
            _log_step(
                processing_log,
                f"打印机返回异常（returncode={result.returncode}），任务可能未入队：{err}。"
                f"请检查 CUPS 服务（如 lpstat -r 是否连接正常）",
                "error",
            )
            return {
                "success": False,
                "printer": printer_name,
                "job_id": job_id,
                "message": f"lp 返回异常（returncode={result.returncode}），打印机可能未收到任务：{err}",
                "queue_confirmed": False,
                "returncode": result.returncode,
            }

        logger.info(f"打印任务已提交，job_id={job_id or 'unknown'}, returncode={result.returncode}")
        if job_id:
            _log_step(
                processing_log,
                f"任务已加入打印机队列（{job_id}）。若前面还有未完成任务，请稍候出纸",
                "success",
            )
        else:
            _log_step(
                processing_log,
                "任务已提交到打印机（未返回任务号，请稍后确认是否出纸）",
                "warning",
            )
        return {
            "success": True,
            "printer": printer_name,
            "job_id": job_id,
            "message": output or "打印任务已提交",
            "queue_confirmed": queue_confirmed,
            "returncode": result.returncode,
        }
    except Exception as e:
        logger.error(f"打印PDF出错: {str(e)}", exc_info=True)
        _log_step(processing_log, f"打印过程出错：{e}", "error")
        return {"success": False, "message": str(e), "queue_confirmed": False}