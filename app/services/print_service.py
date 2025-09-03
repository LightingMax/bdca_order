import os
import platform
import subprocess
import requests
import tempfile
from flask import current_app
from app.config import Config
from app.services.config_service import ConfigService

def get_available_printers():
    """获取系统可用的打印机列表"""
    logger = current_app.logger
    logger.info("正在获取可用打印机列表")
    
    try:
        # 通过配置服务获取API配置
        api_url = ConfigService.get_print_api_url('printers')
        headers = ConfigService.get_auth_headers()
        
        logger.debug(f"正在请求打印机API: {api_url}")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                printers = data["printers"]
                logger.info(f"通过API找到 {len(printers)} 个打印机")
                return printers
            else:
                logger.warning(f"API返回错误: {data['message']}")
                return []
        else:
            logger.error(f"API请求失败，状态码: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"获取打印机列表出错: {str(e)}", exc_info=True)
        return []

def print_pdf(pdf_path, printer_name=None):
    """打印PDF文件 - 直接调用linux_enhanced.py中的函数"""
    logger = current_app.logger
    logger.info(f"开始打印PDF文件: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"找不到文件: {pdf_path}")
        raise FileNotFoundError(f"找不到文件: {pdf_path}")
    
    try:
        # 如果未指定打印机，使用默认打印机
        if not printer_name:
            printer_name = Config.DEFAULT_PRINTER_NAME
            logger.debug(f"使用默认打印机: {printer_name}")
        
        logger.debug(f"开始直接调用智能打印函数，打印机: {printer_name}")
        
        # 直接调用linux_enhanced.py中的函数进行打印
        import sys
        
        # 添加项目根目录到Python路径
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, project_root)
        
        from print_api_service_linux_enhanced import smart_print_pdf
        
        # 设置打印选项
        print_options = {
            'copies': '1',
            'tray': 'auto'
        }
        
        # 直接调用智能打印函数
        success = smart_print_pdf(printer_name, pdf_path, print_options)
        
        if success:
            logger.info(f"打印任务已提交")
            return {"success": True, "printer": printer_name, "job_id": "direct_call"}
        else:
            error_msg = "智能打印函数返回失败"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    except ImportError as e:
        error_msg = f"导入智能打印函数失败: {e}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        logger.error(f"打印PDF出错: {str(e)}", exc_info=True)
        return {"success": False, "message": str(e)}