import os
import platform
import subprocess
import requests
import tempfile
from flask import current_app

def get_available_printers():
    """获取系统可用的打印机列表"""
    logger = current_app.logger
    logger.info("正在获取可用打印机列表")
    
    try:
        # 通过API获取打印机列表
        api_url = "http://192.168.10.87:50003/printers"
        headers = {"Authorization": f"Bearer TOKEN_PRINT_API_KEY_9527"}
        
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

def print_pdf(pdf_path, printer_name="NPIDC0D3D (HP LaserJet MFP M437-M443)"):
    """打印PDF文件"""
    logger = current_app.logger
    logger.info(f"开始打印PDF文件: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"找不到文件: {pdf_path}")
        raise FileNotFoundError(f"找不到文件: {pdf_path}")
    
    try:
        # 通过API发送打印请求
        api_url = "http://192.168.10.87:50003/print"
        headers = {"Authorization": f"Bearer TOKEN_PRINT_API_KEY_9527"}
        
        # 如果未指定打印机，使用默认打印机
        if not printer_name:
            printer_name = "NPIDC0D3D (HP LaserJet MFP M437-M443)"
            logger.debug(f"使用默认打印机: {printer_name}")
        
        logger.debug(f"正在发送文件到打印API，打印机: {printer_name}")
        
        # 修改请求格式，确保参数正确传递
        with open(pdf_path, 'rb') as pdf_file:
            files = {'file': (os.path.basename(pdf_path), pdf_file, 'application/pdf')}
            # 将printer_name作为查询参数而不是表单数据
            response = requests.post(
                f"{api_url}?printer_name={printer_name}",
                headers=headers,
                files=files
            )
        
        # 记录完整的请求和响应信息，便于调试
        logger.debug(f"API请求URL: {api_url}?printer_name={printer_name}")
        logger.debug(f"API响应状态码: {response.status_code}")
        logger.debug(f"API响应内容: {response.text[:500]}")  # 只记录前500个字符，避免日志过大
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                logger.info(f"打印任务已提交，任务ID: {data.get('job_id')}")
                return {"success": True, "printer": printer_name, "job_id": data.get('job_id')}
            else:
                error_msg = f"打印API返回错误: {data['message']}"
                logger.error(error_msg)
                raise Exception(error_msg)
        else:
            error_msg = f"打印API请求失败，状态码: {response.status_code}, 响应: {response.text[:200]}"
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