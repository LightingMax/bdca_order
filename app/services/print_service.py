import os
import re
import shutil
import subprocess
import uuid
from flask import current_app
from app.config import Config

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


def prepare_raw_pdf_for_a4_print(pdf_path, dpi=220):
    """将原始PDF按原尺寸放到A4白纸上，仅供原始打印路径使用。"""
    logger = current_app.logger
    if not str(pdf_path).lower().endswith(".pdf"):
        return pdf_path

    try:
        from pdf2image import convert_from_path
        from PIL import Image

        images = convert_from_path(pdf_path, dpi=dpi)
        if not images:
            return pdf_path

        a4_width = int(8.27 * dpi)
        a4_height = int(11.69 * dpi)
        pages = []

        for image in images:
            image = image.convert("RGB")
            # 保持原物理尺寸；只有当原页超过A4时才缩小以避免裁切。
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
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_on_a4_{uuid.uuid4().hex[:8]}.pdf")
        pages[0].save(
            output_path,
            "PDF",
            resolution=float(dpi),
            save_all=len(pages) > 1,
            append_images=pages[1:],
        )
        logger.info(f"原始PDF已按原尺寸放置到A4页面: {output_path}")
        return output_path
    except Exception as e:
        logger.warning(f"原始PDF A4承载页生成失败，将直接打印原文件: {e}")
        return pdf_path


def print_pdf(pdf_path, printer_name=None, copies=1, media_source=None):
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
            return {"success": False, "message": error_msg}

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
            return {"success": False, "message": f"lp 提交失败: {err}"}
        if result.returncode != 0 and output_indicates_success:
            logger.warning(
                f"lp 返回码非0但输出显示成功，按成功处理: returncode={result.returncode}, output={combined_output}"
            )

        # 常见输出: request id is HP_M437_ULD-123 (1 file(s))
        output = combined_output
        job_id = ""
        match = re.search(r"request id is\s+(\S+)", output, re.IGNORECASE)
        if match:
            job_id = match.group(1)

        logger.info(f"打印任务已提交，job_id={job_id or 'unknown'}, returncode={result.returncode}")
        return {
            "success": True,
            "printer": printer_name,
            "job_id": job_id,
            "message": output or "打印任务已提交",
            "returncode": result.returncode,
        }
    except Exception as e:
        logger.error(f"打印PDF出错: {str(e)}", exc_info=True)
        return {"success": False, "message": str(e)}