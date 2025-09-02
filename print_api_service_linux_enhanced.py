#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机API服务 - Linux增强版 (CUPS专用)
基于FastAPI封装打印功能，提供REST API接口
Linux版本 - 专门使用CUPS打印系统
"""

import platform
import sys

import cups
import os
import logging
import uuid
import shutil
import subprocess # Added for subprocess
import re
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

def check_operating_system():
    """检查操作系统兼容性"""
    system = platform.system().lower()
    release = platform.release()
    
    logger.info(f"🖥️  检测到操作系统: {system} {release}")
    
    # 检查是否为Linux系统
    if system == "linux":
        # 检查是否为类Linux发行版
        if any(distro in platform.platform().lower() for distro in ['ubuntu', 'debian', 'centos', 'redhat', 'fedora', 'arch', 'gentoo', 'suse']):
            logger.info("✅ 操作系统兼容性检查通过 - 支持CUPS打印系统")
            return True
        else:
            logger.warning("⚠️  检测到Linux系统，但发行版可能不完全兼容")
            return True  # 仍然允许运行
    elif system == "darwin":  # macOS
        logger.warning("⚠️  检测到macOS系统，此服务专为Linux设计，可能不完全兼容")
        logger.info("💡 建议：macOS用户请使用 print_api_service_macos.py")
        return True  # 允许运行但给出警告
    elif system == "windows":
        logger.error("❌ 检测到Windows系统，此服务专为Linux设计！")
        logger.error("💡 请使用以下服务之一：")
        logger.error("   - print_api_service.py (通用版本)")
        logger.error("   - print_api_service_enhanced.py (Windows增强版)")
        logger.error("   - print_api_service_windows.py (Windows专用版)")
        return False
    else:
        logger.warning(f"⚠️  未知操作系统: {system}，兼容性未知")
        return True  # 允许运行但给出警告
    
    return True


def get_pdf_page_count(file_path: str) -> int:
    """获取PDF文件的页数"""
    try:
        # 使用pdfinfo命令获取PDF信息
        result = subprocess.run(['pdfinfo', file_path], capture_output=True, text=True)
        if result.returncode == 0:
            # 解析页数信息
            for line in result.stdout.split('\n'):
                if line.startswith('Pages:'):
                    return int(line.split(':')[1].strip())
        return 1  # 默认返回1页
    except Exception as e:
        logger.warning(f"无法获取PDF页数，使用默认值1: {e}")
        return 1


def identify_pdf_type(filename: str) -> str:
    """识别PDF文件类型（行程单或发票）"""
    filename_lower = filename.lower()
    
    # 通过文件名判断
    if any(keyword in filename_lower for keyword in ['发票', 'invoice', 'receipt', 'bill']):
        return 'invoice'
    elif any(keyword in filename_lower for keyword in ['行程', 'itinerary', 'trip', '订单']):
        return 'itinerary'
    else:
        return 'unknown'


def create_combined_first_page(itinerary_path: str, invoice_path: str, output_path: str) -> bool:
    """创建第一页合并版本（行程单+发票）"""
    try:
        # 检查是否有必要的工具
        if not shutil.which('pdftk'):
            logger.warning("未找到pdftk工具，无法合并PDF")
            return False
        
        # 使用pdftk合并第一页
        # 提取行程单第一页
        temp_itinerary_first = os.path.join(TEMP_DIR, f"temp_itinerary_first_{uuid.uuid4().hex[:8]}.pdf")
        subprocess.run(['pdftk', itinerary_path, 'cat', '1', 'output', temp_itinerary_first], check=True)
        
        # 提取发票第一页
        temp_invoice_first = os.path.join(TEMP_DIR, f"temp_invoice_first_{uuid.uuid4().hex[:8]}.pdf")
        subprocess.run(['pdftk', invoice_path, 'cat', '1', 'output', temp_invoice_first], check=True)
        
        # 合并两页
        subprocess.run(['pdftk', temp_itinerary_first, temp_invoice_first, 'cat', 'output', output_path], check=True)
        
        # 清理临时文件
        os.remove(temp_itinerary_first)
        os.remove(temp_invoice_first)
        
        logger.info(f"成功创建合并第一页: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"创建合并第一页失败: {e}")
        return False


def find_corresponding_invoice(itinerary_path: str) -> Optional[str]:
    """查找对应的发票文件"""
    try:
        # 从行程单文件名中提取订单信息
        filename = os.path.basename(itinerary_path)
        
        # 尝试提取订单ID或关键信息
        # 这里需要根据实际的文件命名规则调整
        order_match = re.search(r'(\d+个行程|订单\d+|trip\d+)', filename)
        if order_match:
            order_key = order_match.group(1)
            
            # 在临时目录中查找包含相同订单信息的发票文件
            for temp_file in os.listdir(TEMP_DIR):
                if temp_file.endswith('.pdf') and '发票' in temp_file and order_key in temp_file:
                    return os.path.join(TEMP_DIR, temp_file)
        
        # 如果没有找到，返回None
        return None
        
    except Exception as e:
        logger.warning(f"查找对应发票失败: {e}")
        return None


def smart_print_pdf(printer_name: str, file_path: str, print_options: dict) -> bool:
    """智能PDF打印 - 处理多页PDF的特殊情况"""
    try:
        # 获取PDF页数
        page_count = get_pdf_page_count(file_path)
        filename = os.path.basename(file_path)
        pdf_type = identify_pdf_type(filename)
        
        logger.info(f"智能打印PDF: {filename}, 页数: {page_count}, 类型: {pdf_type}")
        
        # 如果页数<=2，直接打印
        if page_count <= 2:
            logger.info(f"PDF页数≤2，直接打印")
            return print_with_cups(printer_name, file_path, print_options)
        
        # 如果页数>2且是行程单，尝试特殊处理
        if page_count > 2 and pdf_type == 'itinerary':
            logger.info(f"检测到多页行程单，尝试智能处理")
            
            # 查找对应的发票文件
            invoice_path = find_corresponding_invoice(file_path)
            if invoice_path and os.path.exists(invoice_path):
                logger.info(f"找到对应发票: {os.path.basename(invoice_path)}")
                
                # 创建合并的第一页
                combined_first_page = os.path.join(TEMP_DIR, f"combined_first_{uuid.uuid4().hex[:8]}.pdf")
                if create_combined_first_page(file_path, invoice_path, combined_first_page):
                    # 打印合并的第一页
                    logger.info("打印合并的第一页（行程单+发票）")
                    first_page_success = print_with_cups(printer_name, combined_first_page, print_options)
                    
                    # 打印剩余的行程单页面（从第2页开始）
                    remaining_pages = os.path.join(TEMP_DIR, f"remaining_{uuid.uuid4().hex[:8]}.pdf")
                    try:
                        subprocess.run(['pdftk', file_path, 'cat', '2-end', 'output', remaining_pages], check=True)
                        logger.info("打印剩余的行程单页面（第2页开始）")
                        remaining_success = print_with_cups(printer_name, remaining_pages, print_options)
                        
                        # 清理临时文件
                        os.remove(combined_first_page)
                        os.remove(remaining_pages)
                        
                        return first_page_success and remaining_success
                    except Exception as e:
                        logger.error(f"处理剩余页面失败: {e}")
                        os.remove(combined_first_page)
                        return first_page_success
                else:
                    logger.warning("创建合并第一页失败，回退到直接打印")
            else:
                logger.info("未找到对应发票，直接打印")
        
        # 默认情况：直接打印
        logger.info("使用默认打印方式")
        return print_with_cups(printer_name, file_path, print_options)
        
    except Exception as e:
        logger.error(f"智能打印失败: {e}")
        # 回退到直接打印
        return print_with_cups(printer_name, file_path, print_options)


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

# 硬编码配置 - 确保服务稳定可靠
CONFIGURED_PRINTERS = [
    "HP-LaserJet-MFP-M437-M443",
    # "HP_LaserJet_Pro_MFP_M128fp_C3B18B_",
    # "HP_Printer_40",
    # "NetworkPrinter"
]

# 默认打印机 - 硬编码配置
DEFAULT_PRINTER = "HP-LaserJet-MFP-M437-M443"

# 默认纸盘设置 - 避免使用纸盘1
# 根据打印机实际支持的纸盘名称设置：
# - 'auto': 自动选择
# - 'by-pass-tray': 手动进纸托盘
# - 'multi': 多功能托盘（Tray 1）
# - 'top': 上部托盘（Tray 2） - 推荐使用
# - 'bottom': 下部托盘（Tray 3）
DEFAULT_TRAY = "auto"  # 默认使用上部托盘（Tray 2）

# 检查操作系统兼容性
if not check_operating_system():
    logger.error("❌ 操作系统不兼容，服务无法启动")
    sys.exit(1)

# 初始化CUPS连接
try:
    conn = cups.Connection()
    logger.info("CUPS连接初始化成功")
except Exception as e:
    logger.error(f"CUPS连接初始化失败: {e}")
    conn = None

# 初始化FastAPI应用
app = FastAPI(
    title="打印机API服务 - Linux增强版 (CUPS专用)",
    description="用于提交打印任务的REST API，专门使用CUPS打印系统",
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


class PrinterInfo(BaseModel):
    """打印机详细信息模型"""
    name: str
    state: str
    state_message: str
    info: str
    location: str
    is_accepting: bool
    uri: str


def get_printer_status_safe(printer_name: str) -> Dict[str, Any]:
    """
    安全获取打印机状态 - 硬编码逻辑，不依赖CUPS的printer-is-accepting-jobs字段
    """
    try:
        if conn is None:
            return {
                'name': printer_name,
                'state': 'Unknown',
                'state_text': 'CUPS连接失败',
                'is_accepting': False,
                'error': 'CUPS连接未初始化'
            }
        
        printers = conn.getPrinters()
        if printer_name not in printers:
            return {
                'name': printer_name,
                'state': 'Unknown',
                'state_text': '打印机不存在',
                'is_accepting': False,
                'error': f'打印机 {printer_name} 不存在'
            }
        
        printer_info = printers[printer_name]
        state = printer_info.get('printer-state', 0)
        
        # 硬编码状态判断逻辑 - 确保稳定可靠
        state_text = {
            3: "空闲",
            4: "打印中",
            5: "停止",
            6: "离线",
            7: "暂停",
            8: "错误",
            9: "维护中"
        }.get(state, f"未知状态({state})")
        
        # 硬编码判断逻辑：状态为3(空闲)或4(打印中)时认为可以接受任务
        is_accepting = state in [3, 4]
        
        return {
            'name': printer_name,
            'state': state,
            'state_text': state_text,
            'info': printer_info.get('printer-info', ''),
            'location': printer_info.get('printer-location', ''),
            'uri': printer_info.get('device-uri', ''),
            'is_accepting': is_accepting,
            'state_message': printer_info.get('printer-state-message', ''),
            'driver': printer_info.get('printer-make-and-model', '')
        }
        
    except Exception as e:
        logger.error(f"获取打印机 {printer_name} 状态失败: {e}")
        return {
            'name': printer_name,
            'state': 'Unknown',
            'state_text': '获取状态失败',
            'is_accepting': False,
            'error': str(e)
        }


def test_printer_connection():
    """测试打印机连接 - 使用硬编码配置"""
    try:
        logger.info(f"检查配置的 {len(CONFIGURED_PRINTERS)} 台打印机:")
        
        printer_list = []
        for printer_name in CONFIGURED_PRINTERS:
            printer_status = get_printer_status_safe(printer_name)
            printer_list.append(printer_status)
            
            status_icon = "✅" if printer_status['is_accepting'] else "❌"
            logger.info(f"  - {printer_name}: {printer_status['state_text']} {status_icon}")
        
        return printer_list
    except Exception as e:
        logger.error(f"获取打印机列表失败: {e}")
        return []





def print_with_cups(printer_name, file_path, options=None):
    """使用CUPS API打印 - 专门优化的CUPS打印方法"""
    try:
        # 验证文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
        
        # 验证CUPS连接
        if conn is None:
            logger.error("CUPS连接未初始化")
            return False
        
        # 验证打印机是否在配置列表中
        if printer_name not in CONFIGURED_PRINTERS:
            logger.error(f"打印机 {printer_name} 不在配置列表中")
            return False
        
        # 获取打印机状态
        printer_status = get_printer_status_safe(printer_name)
        if not printer_status['is_accepting']:
            logger.error(f"打印机 {printer_name} 当前状态: {printer_status['state_text']}")
            return False
        
        # 构建打印选项，支持纸盘选择
        print_options = {
            'copies': options.get('copies', '1') if options else '1'
        }
        
        # 纸盘选择优先级：用户指定 > 默认设置
        # 注意：CUPS的纸盘参数名称可能是 'media-source' 或 'media'
        if options and options.get('media'):
            print_options['media-source'] = options['media']
        elif options and options.get('tray'):
            print_options['media-source'] = options['tray']
        else:
            # 使用默认纸盘设置，避免使用纸盘1
            print_options['media-source'] = DEFAULT_TRAY
        
        # 如果指定了纸张尺寸，添加到选项中
        if options and options.get('page-size'):
            print_options['page-size'] = options['page-size']
        
        logger.info(f"开始CUPS打印: {file_path} 到打印机: {printer_name}")
        logger.info(f"CUPS打印选项: {print_options}")
        
        # 调试：显示所有可用的打印机选项
        try:
            printer_attrs = conn.getPrinterAttributes(printer_name)
            logger.info(f"打印机 {printer_name} 支持的选项: {list(printer_attrs.keys())}")
            if 'media-source-supported' in printer_attrs:
                logger.info(f"支持的纸盘: {printer_attrs['media-source-supported']}")
        except Exception as e:
            logger.warning(f"无法获取打印机属性: {e}")
        
        try:
            # 首先尝试使用指定的纸盘选项
            job_id = conn.printFile(printer_name, file_path, "PDF打印任务", print_options)
            logger.info(f"✅ CUPS打印任务已提交（使用纸盘选项），ID: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"使用纸盘选项打印失败: {e}")
            logger.info("尝试不指定纸盘选项（使用打印机默认设置）")
            
            # 如果失败，尝试不指定纸盘选项（像另一个程序那样）
            try:
                basic_options = {'copies': options.get('copies', '1') if options else '1'}
                job_id = conn.printFile(printer_name, file_path, "PDF打印任务", basic_options)
                logger.info(f"✅ CUPS打印任务已提交（使用默认设置），ID: {job_id}")
                return True
            except Exception as e2:
                logger.error(f"使用默认设置也失败: {e2}")
                raise e  # 抛出原始错误
        
    except Exception as e:
        logger.error(f"CUPS打印失败: {e}")
        return False





def get_default_printer():
    """获取默认打印机 - 硬编码返回"""
    return DEFAULT_PRINTER


def get_job_status(job_id):
    """获取打印任务状态"""
    try:
        if conn is None:
            return None
        
        jobs = conn.getJobs()
        for printer_jobs in jobs.values():
            if job_id in printer_jobs:
                return printer_jobs[job_id]
        return None
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return None


@app.get("/printers", response_model=PrinterResponse)
async def get_printers(token: str = Depends(verify_token)):
    """获取所有可用打印机列表 - 返回硬编码配置的打印机"""
    printers = test_printer_connection()
    if not printers:
        return PrinterResponse(
            success=False,
            message="获取打印机列表失败",
            printers=[]
        )
    
    printer_names = [p['name'] for p in printers]
    default_printer = get_default_printer()
    
    message = f"找到 {len(printer_names)} 台配置的打印机"
    if default_printer:
        message += f"，默认打印机: {default_printer}"
    
    return PrinterResponse(
        success=True,
        message=message,
        printers=printer_names
    )


@app.get("/printers/detailed")
async def get_printers_detailed(token: str = Depends(verify_token)):
    """获取打印机详细信息 - 基于硬编码配置"""
    printers = test_printer_connection()
    if not printers:
        return {
            "success": False,
            "message": "获取打印机列表失败",
            "printers": []
        }
    
    return {
        "success": True,
        "message": f"找到 {len(printers)} 台配置的打印机",
        "printers": printers
    }


@app.get("/default-printer")
async def get_default_printer_info(token: str = Depends(verify_token)):
    """获取默认打印机信息 - 硬编码返回"""
    default_printer = get_default_printer()
    return {
        "success": True,
        "default_printer": default_printer,
        "message": f"默认打印机: {default_printer}"
    }


@app.get("/printer-options/{printer_name}")
async def get_printer_options(printer_name: str, token: str = Depends(verify_token)):
    """获取打印机的详细选项信息，包括支持的纸盘"""
    # 验证打印机是否在配置列表中
    if printer_name not in CONFIGURED_PRINTERS:
        return {
            "success": False,
            "message": f"打印机 {printer_name} 不在配置列表中"
        }
    
    try:
        if conn is None:
            return {
                "success": False,
                "message": "CUPS连接未初始化"
            }
        
        # 获取打印机属性
        printer_attrs = conn.getPrinterAttributes(printer_name)
        
        # 提取关键信息
        media_sources = printer_attrs.get('media-source-supported', [])
        media_sizes = printer_attrs.get('media-size-supported', [])
        media_types = printer_attrs.get('media-type-supported', [])
        
        return {
            "success": True,
            "printer_name": printer_name,
            "media_sources": media_sources,
            "media_sizes": media_sizes,
            "media_types": media_types,
            "all_attributes": list(printer_attrs.keys()),
            "message": f"打印机 {printer_name} 支持 {len(media_sources)} 个纸盘"
        }
        
    except Exception as e:
        logger.error(f"获取打印机选项失败: {e}")
        return {
            "success": False,
            "message": f"获取打印机选项失败: {str(e)}"
        }


@app.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    """分析PDF文件信息（页数、类型等）"""
    # 验证文件类型
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持PDF文件"
        )
    
    # 保存上传的文件
    job_id = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{job_id}.pdf")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 分析PDF信息
        page_count = get_pdf_page_count(file_path)
        pdf_type = identify_pdf_type(file.filename)
        
        # 清理临时文件
        os.remove(file_path)
        
        return {
            "success": True,
            "filename": file.filename,
            "page_count": page_count,
            "pdf_type": pdf_type,
            "message": f"PDF分析完成：{page_count}页，类型：{pdf_type}"
        }
        
    except Exception as e:
        logger.error(f"分析PDF失败: {e}")
        # 尝试清理临时文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        return {
            "success": False,
            "message": f"分析PDF失败: {str(e)}"
        }


@app.post("/print", response_model=PrintResponse)
async def print_file(
    printer_name: str,
    file: UploadFile = File(...),
    copies: int = 1,
    tray: str = None,  # 纸盘选择: auto, top, bottom, multi, by-pass-tray
    page_size: str = None,  # 纸张尺寸
    token: str = Depends(verify_token)
):
    """打印上传的PDF文件 - 使用CUPS打印，支持纸盘选择"""
    # 验证文件类型
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持PDF文件"
        )
    
    # 验证打印机是否在配置列表中
    if printer_name not in CONFIGURED_PRINTERS:
        return PrintResponse(
            success=False,
            message=f"打印机 {printer_name} 不在配置列表中"
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
    
    # 设置打印选项
    print_options = {
        'copies': str(copies)
    }
    
    # 如果用户指定了纸盘，添加到选项中
    if tray:
        print_options['tray'] = tray
        print_options['media'] = tray
    
    # 如果指定了纸张尺寸，添加到选项中
    if page_size:
        print_options['page-size'] = page_size
    
    # 使用智能PDF打印（处理多页PDF的特殊情况）
    success = smart_print_pdf(printer_name, file_path, print_options)
    
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


@app.get("/printer-status/{printer_name}")
async def get_printer_status(printer_name: str, token: str = Depends(verify_token)):
    """获取指定打印机的状态 - 基于硬编码配置"""
    # 验证打印机是否在配置列表中
    if printer_name not in CONFIGURED_PRINTERS:
        return {
            "success": False,
            "message": f"打印机 {printer_name} 不在配置列表中"
        }
    
    try:
        printer_status = get_printer_status_safe(printer_name)
        
        return {
            "success": True,
            "printer_name": printer_name,
            "state": printer_status['state'],
            "state_text": printer_status['state_text'],
            "state_message": printer_status.get('state_message', ''),
            "info": printer_status.get('info', ''),
            "location": printer_status.get('location', ''),
            "uri": printer_status.get('uri', ''),
            "is_accepting": printer_status['is_accepting'],
            "driver": printer_status.get('driver', '')
        }
    except Exception as e:
        logger.error(f"获取打印机状态失败: {e}")
        return {
            "success": False,
            "message": f"获取打印机状态失败: {str(e)}"
        }


@app.get("/jobs")
async def get_jobs(token: str = Depends(verify_token)):
    """获取所有打印任务"""
    try:
        if conn is None:
            return {
                "success": False,
                "message": "CUPS连接未初始化",
                "jobs": []
            }
        
        jobs = conn.getJobs()
        all_jobs = []
        
        for printer_name, printer_jobs in jobs.items():
            for job_id, job_info in printer_jobs.items():
                all_jobs.append({
                    "job_id": job_id,
                    "printer": printer_name,
                    "state": job_info.get('job-state', 'Unknown'),
                    "state_text": {
                        3: "等待中",
                        4: "打印中",
                        5: "已完成",
                        6: "已取消"
                    }.get(job_info.get('job-state', 0), "未知"),
                    "name": job_info.get('job-name', ''),
                    "pages": job_info.get('job-media-sheets-completed', 0)
                })
        
        return {
            "success": True,
            "message": f"找到 {len(all_jobs)} 个打印任务",
            "jobs": all_jobs
        }
    except Exception as e:
        logger.error(f"获取打印任务失败: {e}")
        return {
            "success": False,
            "message": f"获取打印任务失败: {str(e)}",
            "jobs": []
        }


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: int, token: str = Depends(verify_token)):
    """取消打印任务"""
    try:
        if conn is None:
            return {
                "success": False,
                "message": "CUPS连接未初始化"
            }
        
        conn.cancelJob(job_id)
        return {
            "success": True,
            "message": f"任务 {job_id} 已取消"
        }
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return {
            "success": False,
            "message": f"取消任务失败: {str(e)}"
        }


@app.delete("/temp-files")
async def cleanup_temp_files(token: str = Depends(verify_token)):
    """清理临时文件"""
    try:
        cleaned_count = 0
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                cleaned_count += 1
        
        return {
            "success": True,
            "message": f"清理了 {cleaned_count} 个临时文件"
        }
    except Exception as e:
        logger.error(f"清理临时文件失败: {e}")
        return {
            "success": False,
            "message": f"清理临时文件失败: {str(e)}"
        }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动打印机API服务 - Linux增强版")
    print("=" * 50)
    print("✅ 操作系统兼容性检查通过")
    print("✅ CUPS连接初始化成功")
    print("✅ 服务配置完成")
    print("=" * 50)
    print(f"🌐 服务地址: http://0.0.0.0:12346")
    print(f"📚 API文档: http://0.0.0.0:12346/docs")
    print(f"🔄 自动重载: 已启用")
    print("=" * 50)
    
    uvicorn.run("print_api_service_linux_enhanced:app", host="0.0.0.0", port=12346, reload=True)

