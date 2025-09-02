#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机API服务 - 增强版
正确处理PDF渲染和打印流程
"""

import os
import logging
import uuid
import shutil
import subprocess
import platform
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

# API密钥
API_KEY = "TOKEN_PRINT_API_KEY_9527"

# 初始化FastAPI应用
app = FastAPI(
    title="打印机API服务 - 增强版",
    description="正确处理PDF渲染和打印的REST API",
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


def get_printers_system():
    """使用系统命令获取打印机列表"""
    try:
        if platform.system().lower() == "linux":
            result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
            if result.returncode == 0:
                printers = []
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('打印机 '):
                        parts = line.split()
                        if len(parts) >= 2:
                            printer_name = parts[1]
                            printers.append(printer_name)
                return printers
            else:
                logger.error(f"lpstat命令失败: {result.stderr}")
                return []
        else:
            logger.error(f"不支持的操作系统: {platform.system()}")
            return []
    except Exception as e:
        logger.error(f"获取打印机列表失败: {e}")
        return []


def get_default_printer_system():
    """使用系统命令获取默认打印机"""
    try:
        if platform.system().lower() == "linux":
            result = subprocess.run(['lpstat', '-d'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if 'system default destination:' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            return parts[1].strip()
            return None
        else:
            return None
    except Exception as e:
        logger.error(f"获取默认打印机失败: {e}")
        return None


def print_pdf_with_rendering(printer_name, file_path, copies=1):
    """使用正确的PDF渲染方式打印文件"""
    try:
        if platform.system().lower() == "linux":
            # 方法1: 使用lpr命令（推荐）
            cmd = ['lpr', '-P', printer_name]
            if copies > 1:
                cmd.extend(['-#', str(copies)])
            cmd.append(file_path)
            
            logger.info(f"执行PDF打印命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"PDF打印成功: {file_path}")
                return True
            else:
                logger.error(f"PDF打印失败: {result.stderr}")
                
                # 方法2: 尝试使用pdftops转换后打印
                logger.info("尝试使用pdftops转换PDF...")
                return print_pdf_with_pdftops(printer_name, file_path, copies)
        else:
            logger.error(f"不支持的操作系统: {platform.system()}")
            return False
    except Exception as e:
        logger.error(f"PDF打印异常: {e}")
        return False


def print_pdf_with_pdftops(printer_name, file_path, copies=1):
    """使用pdftops转换PDF后打印"""
    try:
        # 检查是否安装了pdftops
        result = subprocess.run(['which', 'pdftops'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("未找到pdftops工具")
            return False
        
        # 创建临时PS文件
        ps_file = file_path.replace('.pdf', '.ps')
        
        # 转换PDF到PS
        convert_cmd = ['pdftops', file_path, ps_file]
        logger.info(f"转换PDF到PS: {' '.join(convert_cmd)}")
        
        result = subprocess.run(convert_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"PDF转换失败: {result.stderr}")
            return False
        
        # 打印PS文件
        print_cmd = ['lpr', '-P', printer_name]
        if copies > 1:
            print_cmd.extend(['-#', str(copies)])
        print_cmd.append(ps_file)
        
        logger.info(f"打印PS文件: {' '.join(print_cmd)}")
        result = subprocess.run(print_cmd, capture_output=True, text=True)
        
        # 清理临时文件
        try:
            os.remove(ps_file)
        except:
            pass
        
        if result.returncode == 0:
            logger.info(f"PS打印成功: {ps_file}")
            return True
        else:
            logger.error(f"PS打印失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"pdftops打印异常: {e}")
        return False


def print_pdf_with_ghostscript(printer_name, file_path, copies=1):
    """使用Ghostscript打印PDF"""
    try:
        # 检查是否安装了Ghostscript
        result = subprocess.run(['which', 'gs'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("未找到Ghostscript工具")
            return False
        
        # 使用Ghostscript直接打印
        gs_cmd = [
            'gs', '-dNOPAUSE', '-dBATCH', '-dSAFER',
            f'-sDEVICE=ljet4',  # 使用HP LaserJet驱动
            f'-sOutputFile=%printer%{printer_name}',
            file_path
        ]
        
        logger.info(f"使用Ghostscript打印: {' '.join(gs_cmd)}")
        result = subprocess.run(gs_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Ghostscript打印成功: {file_path}")
            return True
        else:
            logger.error(f"Ghostscript打印失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Ghostscript打印异常: {e}")
        return False


@app.get("/printers", response_model=PrinterResponse)
async def get_printers(token: str = Depends(verify_token)):
    """获取所有可用打印机列表"""
    printers = get_printers_system()
    if not printers:
        return PrinterResponse(
            success=False,
            message="获取打印机列表失败",
            printers=[]
        )
    
    message = f"找到 {len(printers)} 台打印机"
    logger.info(f"API返回打印机列表: {printers}")
    
    return PrinterResponse(
        success=True,
        message=message,
        printers=printers
    )


@app.get("/default-printer")
async def get_default_printer_info(token: str = Depends(verify_token)):
    """获取默认打印机信息"""
    default_printer = get_default_printer_system()
    if default_printer:
        return {
            "success": True,
            "default_printer": default_printer,
            "message": f"默认打印机: {default_printer}"
        }
    else:
        return {
            "success": False,
            "default_printer": None,
            "message": "未找到默认打印机"
        }


@app.post("/print", response_model=PrintResponse)
async def print_file(
    printer_name: str,
    file: UploadFile = File(...),
    copies: int = 1,
    method: str = "lpr",  # 打印方法: lpr, pdftops, ghostscript
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
    printers = get_printers_system()
    if printer_name not in printers:
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
    
    # 根据方法选择打印方式
    success = False
    if method == "lpr":
        success = print_pdf_with_rendering(printer_name, file_path, copies)
    elif method == "pdftops":
        success = print_pdf_with_pdftops(printer_name, file_path, copies)
    elif method == "ghostscript":
        success = print_pdf_with_ghostscript(printer_name, file_path, copies)
    else:
        return PrintResponse(
            success=False,
            message=f"不支持的打印方法: {method}"
        )
    
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


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "print_api_service_enhanced",
        "version": "1.0.0",
        "features": ["pdf_rendering", "multiple_print_methods"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=12346)
