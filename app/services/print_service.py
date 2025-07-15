import os
import platform
import subprocess
from flask import current_app

def get_available_printers():
    """获取系统可用的打印机列表"""
    logger = current_app.logger
    logger.info("正在获取可用打印机列表")
    
    printers = []
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows系统使用win32print
            logger.debug("检测到Windows系统，使用win32print获取打印机列表")
            import win32print
            printers = [printer[2] for printer in win32print.EnumPrinters(2)]
            logger.info(f"找到 {len(printers)} 个打印机")
        
        elif system == "Linux":
            # Linux系统使用CUPS
            logger.debug("检测到Linux系统，尝试使用CUPS或lpstat获取打印机列表")
            try:
                import cups
                conn = cups.Connection()
                printers = list(conn.getPrinters().keys())
                logger.info(f"使用CUPS找到 {len(printers)} 个打印机")
            except ImportError:
                # 如果没有CUPS，尝试使用lp命令
                logger.debug("CUPS不可用，尝试使用lpstat命令")
                result = subprocess.run(['lpstat', '-a'], stdout=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    printers = [line.split()[0] for line in lines if line]
                    logger.info(f"使用lpstat找到 {len(printers)} 个打印机")
                else:
                    logger.warning("lpstat命令执行失败")
        
        elif system == "Darwin":  # macOS
            # macOS使用CUPS或lp命令
            logger.debug("检测到macOS系统，尝试使用CUPS或lpstat获取打印机列表")
            try:
                import cups
                conn = cups.Connection()
                printers = list(conn.getPrinters().keys())
                logger.info(f"使用CUPS找到 {len(printers)} 个打印机")
            except ImportError:
                logger.debug("CUPS不可用，尝试使用lpstat命令")
                result = subprocess.run(['lpstat', '-a'], stdout=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    printers = [line.split()[0] for line in lines if line]
                    logger.info(f"使用lpstat找到 {len(printers)} 个打印机")
                else:
                    logger.warning("lpstat命令执行失败")
        else:
            logger.warning(f"不支持的操作系统: {system}")
    
    except Exception as e:
        logger.error(f"获取打印机列表出错: {str(e)}", exc_info=True)
    
    return printers

def print_pdf(pdf_path, printer_name=None):
    """打印PDF文件"""
    logger = current_app.logger
    logger.info(f"开始打印PDF文件: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"找不到文件: {pdf_path}")
        raise FileNotFoundError(f"找不到文件: {pdf_path}")
    
    system = platform.system()
    logger.debug(f"检测到操作系统: {system}")
    
    try:
        if system == "Windows":
            # Windows系统使用win32print
            logger.debug("使用win32print进行打印")
            import win32print
            import win32api
            
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()
                logger.debug(f"使用默认打印机: {printer_name}")
            
            win32api.ShellExecute(0, "print", pdf_path, f'/d:"{printer_name}"', ".", 0)
            logger.info(f"文件已发送到打印机: {printer_name}")
            return {"success": True, "printer": printer_name}
        
        elif system == "Linux" or system == "Darwin":  # Linux或macOS
            # 尝试使用lp命令
            logger.debug("使用lp命令进行打印")
            cmd = ['lp', pdf_path]
            if printer_name:
                cmd.extend(['-d', printer_name])
                logger.debug(f"指定打印机: {printer_name}")
            else:
                logger.debug("使用默认打印机")
            
            logger.debug(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                logger.info("打印命令执行成功")
                return {"success": True, "printer": printer_name or "默认打印机"}
            else:
                error_msg = f"打印命令失败: {result.stderr}"
                logger.error(error_msg)
                raise Exception(error_msg)
        
        else:
            error_msg = f"不支持的操作系统: {system}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    except Exception as e:
        logger.error(f"打印PDF出错: {str(e)}", exc_info=True)
        # 在开发环境中，如果打印失败，可以选择不抛出异常
        if current_app.config.get('DEBUG', False):
            logger.warning("调试模式：模拟打印成功")
            return {"success": True, "printer": "模拟打印机", "debug": True}
        else:
            raise 