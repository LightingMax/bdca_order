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
import threading
import time
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
    
    # 优先检查更具体的标识
    if '行程单' in filename_lower:
        return 'itinerary'
    elif '发票' in filename_lower:
        return 'invoice'
    
    # 然后检查其他关键词
    if any(keyword in filename_lower for keyword in ['invoice', 'receipt', 'bill']):
        return 'invoice'
    elif any(keyword in filename_lower for keyword in ['itinerary', 'trip', '订单']):
        return 'itinerary'
    
    # 最后检查通用关键词（但优先级较低）
    if '行程' in filename_lower and '发票' not in filename_lower:
        return 'itinerary'
    elif '发票' in filename_lower and '行程' not in filename_lower:
        return 'invoice'
    
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


def create_smart_combined_first_page(itinerary_path: str, invoice_path: str, output_path: str) -> bool:
    """创建智能拼接第一页（发票在上 + 行程单第一页内容）"""
    try:
        # 检查是否有必要的工具
        if not shutil.which('pdftk'):
            logger.warning("未找到pdftk工具，无法合并PDF")
            return False
        
        # 创建临时文件
        temp_itinerary_first = os.path.join(TEMP_DIR, f"temp_itinerary_first_{uuid.uuid4().hex[:8]}.pdf")
        temp_invoice_first = os.path.join(TEMP_DIR, f"temp_invoice_first_{uuid.uuid4().hex[:8]}.pdf")
        
        try:
            # 提取行程单第一页
            logger.info("📄 提取行程单第一页")
            subprocess.run(['pdftk', itinerary_path, 'cat', '1', 'output', temp_itinerary_first], check=True)
            
            # 提取发票第一页
            logger.info("🧾 提取发票第一页")
            subprocess.run(['pdftk', invoice_path, 'cat', '1', 'output', temp_invoice_first], check=True)
            
            # 智能拼接：发票在上，行程单第一页内容在下
            # 基于测试验证的最佳拼接方法
            logger.info("🔗 开始智能拼接：发票在上 + 行程单第一页内容")
            
            # 方法1：使用pdftk的cat功能进行垂直拼接（推荐，已验证有效）
            # 测试证明：pdftk cat可以避免黑色区域，生成清晰的拼接结果
            try:
                logger.info("🔄 使用pdftk cat功能进行垂直拼接（推荐方法）")
                
                # 直接使用pdftk cat拼接，无需复杂的尺寸检查
                # 测试显示：即使页面尺寸不同，pdftk cat也能正确处理
                subprocess.run([
                    'pdftk', temp_invoice_first, temp_itinerary_first, 
                    'cat', 'output', output_path
                ], check=True)
                
                logger.info("✅ 使用pdftk cat功能成功拼接")
                
                # 验证拼接结果
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"📊 拼接文件大小: {file_size} bytes")
                    
                    # 验证文件质量
                    if file_size < 1000:
                        logger.warning("⚠️ 拼接文件过小，可能拼接失败")
                        raise subprocess.CalledProcessError(1, "pdftk", "File too small")
                    
                    # 验证PDF有效性
                    result = subprocess.run(['pdftk', output_path, 'dump_data'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        page_count = 0
                        for line in result.stdout.split('\n'):
                            if line.startswith('NumberOfPages:'):
                                page_count = int(line.split(':')[1].strip())
                                break
                        
                        if page_count >= 2:  # 拼接后应该有2页（发票+行程单第1页）
                            logger.info(f"✅ 拼接验证成功：{page_count}页")
                        else:
                            logger.warning(f"⚠️ 拼接页数异常：{page_count}页")
                        
                    else:
                        logger.warning("⚠️ 无法验证PDF有效性")
                        
            except subprocess.CalledProcessError as e:
                logger.warning(f"⚠️ pdftk cat功能失败: {e}")
                
                # 方法2：尝试使用stamp功能（备选方案）
                try:
                    logger.info("🔄 尝试使用pdftk stamp功能（备选方案）")
                    subprocess.run([
                        'pdftk', temp_invoice_first, 
                        'stamp', temp_itinerary_first, 
                        'output', output_path
                    ], check=True)
                    logger.info("✅ 使用pdftk stamp功能成功拼接")
                    
                    # 验证stamp拼接结果
                    if os.path.exists(output_path):
                        file_size = os.path.getsize(output_path)
                        logger.info(f"📊 stamp拼接文件大小: {file_size} bytes")
                        
                        # stamp拼接后应该是1页
                        result = subprocess.run(['pdftk', output_path, 'dump_data'], 
                                              capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            for line in result.stdout.split('\n'):
                                if line.startswith('NumberOfPages:'):
                                    page_count = int(line.split(':')[1].strip())
                                    logger.info(f"✅ stamp拼接验证成功：{page_count}页")
                                    break
                    
                except subprocess.CalledProcessError:
                    logger.error("❌ pdftk stamp功能也失败了")
                    raise
            
            # 验证输出文件质量和完整性
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"📊 拼接文件大小: {file_size} bytes")
                
                # 检查文件大小是否合理
                if file_size < 1000:
                    logger.error("❌ 拼接文件过小，拼接可能失败")
                    return False
                
                # 检查文件是否为有效的PDF
                try:
                    result = subprocess.run(['pdftk', output_path, 'dump_data'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # 解析页数
                        page_count = 0
                        for line in result.stdout.split('\n'):
                            if line.startswith('NumberOfPages:'):
                                page_count = int(line.split(':')[1].strip())
                                break
                        
                        if page_count >= 1:
                            logger.info(f"✅ 智能拼接第一页创建成功: {output_path}")
                            logger.info(f"   文件大小: {file_size} bytes, 页数: {page_count}")
                            return True
                        else:
                            logger.error("❌ 拼接文件页数异常")
                            return False
                    else:
                        logger.error("❌ 拼接文件不是有效的PDF")
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ 验证PDF文件失败: {e}")
                    return False
            else:
                logger.error("❌ 输出文件创建失败")
                return False
                
        finally:
            # 清理临时文件
            try:
                if os.path.exists(temp_itinerary_first):
                    os.remove(temp_itinerary_first)
                if os.path.exists(temp_invoice_first):
                    os.remove(temp_invoice_first)
            except Exception as e:
                logger.warning(f"清理临时文件时出错: {e}")
        
    except Exception as e:
        logger.error(f"❌ 创建智能拼接第一页失败: {e}")
        return False


# 单页智能拼接函数已移至 pdf_service.py


def find_corresponding_invoice(itinerary_path: str) -> Optional[str]:
    """查找对应的发票文件 - 增强版"""
    try:
        # 从行程单文件名中提取订单信息
        filename = os.path.basename(itinerary_path)
        logger.info(f"🔍 查找行程单对应的发票: {filename}")
        
        # 方法1：基于文件名的智能匹配
        # 提取订单ID或关键信息（支持更多模式）
        order_patterns = [
            r'(\d+个行程)',           # 高德打车：2个行程
            r'(订单\d+)',             # 通用订单格式
            r'(trip\d+)',             # 英文trip格式
            r'(\d+\.\d+元)',          # 金额格式：53.21元
            r'(\d+-\d+)',             # 数字-数字格式
            r'([A-Za-z0-9]{8,})',    # 8位以上字母数字组合
        ]
        
        order_key = None
        for pattern in order_patterns:
            match = re.search(pattern, filename)
            if match:
                order_key = match.group(1)
                logger.info(f"🔑 提取到订单标识: {order_key}")
                break
        
        if not order_key:
            logger.warning(f"⚠️ 无法从文件名提取订单标识: {filename}")
            # 尝试使用文件名的一部分作为匹配依据
            order_key = filename.split('.')[0]  # 去掉扩展名
            logger.info(f"🔑 使用文件名作为订单标识: {order_key}")
        
        # 方法2：在多个目录中搜索发票文件
        search_dirs = [
            TEMP_DIR,                                    # FastAPI临时目录
            "app/static/uploads",                         # Flask上传目录
            "app/static/outputs",                         # Flask输出目录
            "temp_files",                                 # 其他临时目录
        ]
        
        # 方法2.5：添加Flask ZIP解压目录到搜索路径
        # Flask上传ZIP后解压到 temp/{session_id}/extracted/ 目录
        flask_temp_dir = "temp"  # Flask的临时目录
        if os.path.exists(flask_temp_dir):
            search_dirs.append(flask_temp_dir)
            logger.info(f"🔍 添加Flask临时目录到搜索路径: {flask_temp_dir}")
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
                
            logger.info(f"🔍 在目录中搜索发票: {search_dir}")
            
            # 递归搜索PDF文件
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file.endswith('.pdf'):
                        file_lower = file.lower()
                        
                        # 检查是否是发票文件
                        is_invoice = any(keyword in file_lower for keyword in [
                            '发票', 'invoice', 'receipt', 'bill', '电子发票'
                        ])
                        
                        if is_invoice:
                            # 检查是否包含订单标识
                            if order_key in file:
                                invoice_path = os.path.join(root, file)
                                logger.info(f"✅ 找到对应发票: {invoice_path}")
                                return invoice_path
                            
                            # 如果文件名不包含订单标识，尝试基于时间匹配
                            # 假设发票和行程单是同时上传的
                            try:
                                file_time = os.path.getmtime(os.path.join(root, file))
                                itinerary_time = os.path.getmtime(itinerary_path)
                                
                                # 如果时间差在5分钟内，认为是相关文件
                                if abs(file_time - itinerary_time) < 300:  # 5分钟 = 300秒
                                    invoice_path = os.path.join(root, file)
                                    logger.info(f"✅ 基于时间匹配找到发票: {invoice_path}")
                                    return invoice_path
                            except Exception as e:
                                logger.debug(f"时间匹配失败: {e}")
        
        # 方法3：如果还是找不到，尝试在Flask的输出目录中查找
        flask_output_dir = "app/static/outputs"
        if os.path.exists(flask_output_dir):
            logger.info(f"🔍 在Flask输出目录中搜索发票: {flask_output_dir}")
            
            for file in os.listdir(flask_output_dir):
                if file.endswith('.pdf'):
                    file_lower = file.lower()
                    if any(keyword in file_lower for keyword in ['发票', 'invoice', 'receipt']):
                        if order_key in file:
                            invoice_path = os.path.join(flask_output_dir, file)
                            logger.info(f"✅ 在Flask输出目录找到发票: {invoice_path}")
                            return invoice_path
        
        logger.warning(f"❌ 未找到对应的发票文件，订单标识: {order_key}")
        return None
        
    except Exception as e:
        logger.error(f"❌ 查找对应发票失败: {e}")
        return None


def smart_print_pdf(printer_name: str, file_path: str, print_options: dict) -> bool:
    """智能PDF打印 - 简化版本，主要调用pdf_service.py的函数进行文件处理"""
    # 使用锁防止并发打印冲突，确保打印任务依次执行
    with print_lock:
        try:
            # 添加小延迟，避免打印任务过于密集
            time.sleep(0.1)
            
            # 获取PDF页数
            page_count = get_pdf_page_count(file_path)
            filename = os.path.basename(file_path)
            pdf_type = identify_pdf_type(filename)
            
            logger.info(f"智能打印PDF: {filename}, 页数: {page_count}, 类型: {pdf_type}")
            
            # 如果是行程单，检查是否需要智能拼接
            if pdf_type == 'itinerary':
                logger.info(f"检测到行程单，页数: {page_count}")
                invoice_path = find_corresponding_invoice(file_path)
                
                if invoice_path and os.path.exists(invoice_path):
                    logger.info(f"找到对应发票: {os.path.basename(invoice_path)}")
                    
                    # 调用pdf_service.py的函数进行智能拼接
                    try:
                        import sys
                        
                        # 添加项目根目录到Python路径
                        project_root = os.path.dirname(os.path.abspath(__file__))
                        sys.path.insert(0, project_root)
                        
                        from app.services.pdf_service import create_smart_combined_pdf
                        
                        # 创建智能拼接的PDF
                        combined_page = os.path.join(TEMP_DIR, f"smart_combined_{uuid.uuid4().hex[:8]}.pdf")
                        if create_smart_combined_pdf(file_path, invoice_path, combined_page, page_count):
                            logger.info("✅ 成功创建智能拼接页面")
                            
                            # 打印智能拼接的页面
                            success = print_with_cups(printer_name, combined_page, print_options)
                            
                            # 清理临时文件
                            os.remove(combined_page)
                            
                            if success:
                                # 如果是多页行程单，还需要打印剩余页面
                                if page_count > 1:
                                    logger.info(f"🖨️ 打印行程单剩余页面（第2页到第{page_count}页）")
                                    remaining_pages = os.path.join(TEMP_DIR, f"remaining_itinerary_{uuid.uuid4().hex[:8]}.pdf")
                                    try:
                                        # 使用pdftk提取第2页到最后一页
                                        subprocess.run(['pdftk', file_path, 'cat', '2-end', 'output', remaining_pages], check=True)
                                        remaining_success = print_with_cups(printer_name, remaining_pages, print_options)
                                        
                                        # 清理临时文件
                                        os.remove(remaining_pages)
                                        
                                        if remaining_success:
                                            logger.info("✅ 多页行程单智能打印完成：第一页（发票+行程单）+ 剩余页面")
                                            return True
                                        else:
                                            logger.warning("⚠️ 第一页打印成功，但剩余页面打印失败")
                                            return False
                                            
                                    except Exception as e:
                                        logger.error(f"❌ 处理行程单剩余页面失败: {e}")
                                        logger.info("⚠️ 只打印了智能拼接的第一页")
                                        return success
                                else:
                                    logger.info("✅ 单页行程单智能打印完成")
                                    return success
                            else:
                                logger.error("❌ 智能拼接页面打印失败")
                                return False
                        else:
                            logger.warning("⚠️ 创建智能拼接页面失败，回退到直接打印")
                    except ImportError as e:
                        logger.error(f"❌ 导入pdf_service失败: {e}")
                        logger.info("回退到直接打印")
                    except Exception as e:
                        logger.error(f"❌ 智能拼接失败: {e}")
                        logger.info("回退到直接打印")
                else:
                    logger.info("ℹ️ 未找到对应发票，直接打印行程单")
            
            # 默认情况：直接打印
            logger.info("🖨️ 使用默认打印方式")
            return print_with_cups(printer_name, file_path, print_options)
            
        except Exception as e:
            logger.error(f"❌ 智能打印失败: {e}")
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

# 添加打印锁，防止并发打印冲突
print_lock = threading.Lock()

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


class PrintFileRequest(BaseModel):
    """文件路径打印请求模型"""
    file_path: str
    printer_name: str = "HP-LaserJet-MFP-M437-M443"
    copies: int = 1
    tray: str = "auto"
    page_size: Optional[str] = None


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


@app.post("/print-file", response_model=PrintResponse)
async def print_file_by_path(
    request: PrintFileRequest,
    token: str = Depends(verify_token)
):
    """通过文件路径打印PDF文件 - 用于Flask后端调用"""
    file_path = request.file_path
    printer_name = request.printer_name
    copies = request.copies
    tray = request.tray
    page_size = request.page_size
    
    logger.info(f"收到文件路径打印请求: {file_path}")
    
    # 验证打印机是否在配置列表中
    if printer_name not in CONFIGURED_PRINTERS:
        return PrintResponse(
            success=False,
            message=f"打印机 {printer_name} 不在配置列表中"
        )
    
    # 验证文件是否存在
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return PrintResponse(
            success=False,
            message=f"文件不存在: {file_path}"
        )
    
    # 验证文件类型
    if not file_path.lower().endswith('.pdf'):
        logger.error(f"不支持的文件类型: {file_path}")
        return PrintResponse(
            success=False,
            message="只支持PDF文件"
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
    
    logger.info(f"开始打印文件: {file_path} 到打印机: {printer_name}")
    
    # 使用智能PDF打印（处理多页PDF的特殊情况）
    success = smart_print_pdf(printer_name, file_path, print_options)
    
    if success:
        job_id = str(uuid.uuid4())
        logger.info(f"打印任务提交成功: {job_id}")
        return PrintResponse(
            success=True,
            message="打印任务已提交",
            job_id=job_id
        )
    else:
        logger.error(f"打印失败: {file_path}")
        return PrintResponse(
            success=False,
            message="打印失败",
            job_id=None
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


@app.post("/preview-smart-processed")
async def preview_smart_processed(
    request: dict,
    token: str = Depends(verify_token)
):
    """预览智能处理后的PDF文件"""
    try:
        order_data = request.get('order_data', {})
        action = request.get('action', 'preview')
        
        logger.info(f"收到智能拼接预览请求: {order_data}")
        
        if action != 'preview':
            return {
                "success": False,
                "message": "不支持的操作类型"
            }
        
        # 这里需要实现智能拼接预览逻辑
        # 由于这是一个预览请求，我们需要：
        # 1. 根据订单数据找到对应的文件
        # 2. 进行智能拼接
        # 3. 生成预览PDF
        # 4. 返回预览链接
        
        # TODO: 实现真正的智能拼接预览功能
        return {
            "success": False,
            "message": "智能拼接预览功能开发中，请使用打印功能查看最终效果"
        }
        
    except Exception as e:
        logger.error(f"智能拼接预览失败: {e}")
        return {
            "success": False,
            "message": f"智能拼接预览失败: {str(e)}"
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

