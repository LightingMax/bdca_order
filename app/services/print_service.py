import os
import platform
import subprocess
from flask import current_app

def get_available_printers():
    """获取系统可用的打印机列表"""
    printers = []
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows系统使用win32print
            import win32print
            printers = [printer[2] for printer in win32print.EnumPrinters(2)]
        
        elif system == "Linux":
            # Linux系统使用CUPS
            try:
                import cups
                conn = cups.Connection()
                printers = list(conn.getPrinters().keys())
            except ImportError:
                # 如果没有CUPS，尝试使用lp命令
                result = subprocess.run(['lpstat', '-a'], stdout=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    printers = [line.split()[0] for line in lines if line]
        
        elif system == "Darwin":  # macOS
            # macOS使用CUPS或lp命令
            try:
                import cups
                conn = cups.Connection()
                printers = list(conn.getPrinters().keys())
            except ImportError:
                result = subprocess.run(['lpstat', '-a'], stdout=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    printers = [line.split()[0] for line in lines if line]
    
    except Exception as e:
        print(f"获取打印机列表出错: {str(e)}")
    
    return printers

def print_pdf(pdf_path, printer_name=None):
    """打印PDF文件"""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"找不到文件: {pdf_path}")
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Windows系统使用win32print
            import win32print
            import win32api
            
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()
            
            win32api.ShellExecute(0, "print", pdf_path, f'/d:"{printer_name}"', ".", 0)
            return {"success": True, "printer": printer_name}
        
        elif system == "Linux" or system == "Darwin":  # Linux或macOS
            # 尝试使用lp命令
            cmd = ['lp', pdf_path]
            if printer_name:
                cmd.extend(['-d', printer_name])
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                return {"success": True, "printer": printer_name or "默认打印机"}
            else:
                raise Exception(f"打印命令失败: {result.stderr}")
        
        else:
            raise Exception(f"不支持的操作系统: {system}")
    
    except Exception as e:
        print(f"打印PDF出错: {str(e)}")
        # 在开发环境中，如果打印失败，可以选择不抛出异常
        if current_app.config.get('DEBUG', False):
            print("调试模式：模拟打印成功")
            return {"success": True, "printer": "模拟打印机", "debug": True}
        else:
            raise 