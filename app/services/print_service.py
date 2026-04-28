import os
import re
import shutil
import subprocess
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