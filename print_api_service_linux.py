#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机API服务 - Linux版本
基于FastAPI封装打印功能，提供REST API接口
Linux版本 - 使用cups
"""

import cups
import os
import logging
import uuid
import shutil
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建临时文件目录
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# API密钥 - 在生产环境中应该使用更安全的方式存储
API_KEY = "TOKEN_PRINT_API_KEY_9527"

# 初始化CUPS连接
try:
    conn = cups.Connection()
    logger.info("CUPS连接初始化成功")
except Exception as e:
    logger.error(f"CUPS连接初始化失败: {e}")
    conn = None

# 初始化FastAPI应用
app = FastAPI(
    title="打印机API服务 - Linux版本",
    description="用于提交打印任务的REST API (CUPS)",
    version="1.0.0"
)

# 安全验证
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """验证Bearer令牌"""
    if credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


class PrinterResponse(BaseModel):
    """打印机响应模型"""
    success: bool
    message: str
    printers: Optional[List[str]] = None


class PrintResponse(BaseModel):
    """打印响应模型"""
    success: bool
    message: str
    job_id: Optional[str] = None


def test_printer_connection():
    """测试打印机连接"""
    try:
        if conn is None:
            logger.error("CUPS连接未初始化")
            return []
        
        printers = conn.getPrinters()
        logger.info(f"发现 {len(printers)} 台打印机:")
        
        printer_list = []
        for printer_name, printer_info in printers.items():
            logger.info(f"  - {printer_name} ({printer_info.get('printer-state', 'Unknown')})")
            printer_list.append({
                'name': printer_name,
                'state': printer_info.get('printer-state', 'Unknown'),
                'info': printer_info.get('printer-info', ''),
                'location': printer_info.get('printer-location', '')
            })
        
        return printer_list
    except Exception as e:
        logger.error(f"获取打印机列表失败: {e}")
        return []


def print_single_file(printer_name, file_path):
    """打印单个文件"""
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return False
    
    if conn is None:
        logger.error("CUPS连接未初始化")
        return False
    
    try:
        logger.info(f"开始打印: {file_path} 到打印机: {printer_name}")
        
        # 获取打印机信息
        printers = conn.getPrinters()
        if printer_name not in printers:
            logger.error(f"打印机不存在: {printer_name}")
            return False
        
        # 检查打印机状态
        printer_state = printers[printer_name].get('printer-state', 0)
        if printer_state == 3:  # 3表示打印机空闲
            logger.info(f"打印机 {printer_name} 状态正常")
        else:
            logger.warning(f"打印机 {printer_name} 状态: {printer_state}")
        
        # 提交打印任务
        job_id = conn.printFile(printer_name, file_path, "PDF打印任务", {})
        logger.info(f"打印任务已提交，任务ID: {job_id}")
        
        return True
    except Exception as e:
        logger.error(f"打印失败: {e}")
        return False


@app.get("/printers", response_model=PrinterResponse)
async def get_printers(token: str = Depends(verify_token)):
    """获取所有可用打印机列表"""
    printers = test_printer_connection()
    if not printers:
        return PrinterResponse(
            success=False,
            message="获取打印机列表失败",
            printers=[]
        )
    
    printer_names = [p['name'] for p in printers]
    return PrinterResponse(
        success=True,
        message=f"找到 {len(printer_names)} 台打印机",
        printers=printer_names
    )


@app.post("/print", response_model=PrintResponse)
async def print_file(
    printer_name: str,
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    """打印上传的PDF文件"""
    # 验证文件类型
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持PDF文件"
        )
    
    # 验证打印机是否存在
    printers = test_printer_connection()
    printer_exists = False
    for printer in printers:
        if printer['name'] == printer_name:
            printer_exists = True
            break
    
    if not printer_exists:
        return PrintResponse(
            success=False,
            message=f"未找到打印机: {printer_name}"
        )
    
    # 保存上传的文件
    job_id = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{job_id}.pdf")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"保存文件失败: {e}")
        return PrintResponse(
            success=False,
            message=f"保存文件失败: {str(e)}"
        )
    
    # 打印文件
    success = print_single_file(printer_name, file_path)
    
    if success:
        return PrintResponse(
            success=True,
            message="打印任务已提交",
            job_id=job_id
        )
    else:
        return PrintResponse(
            success=False,
            message="打印失败",
            job_id=job_id
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=50003)
