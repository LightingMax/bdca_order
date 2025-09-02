#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试纸盘设置的脚本
专门用于解决纸盘1没有纸的问题
"""

import os
import subprocess
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
PRINTER_NAME = "HP-LaserJet-MFP-M437-M443"
TEST_PDF = "test_tray.pdf"

def create_test_pdf():
    """创建测试PDF"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        os.makedirs("temp_files", exist_ok=True)
        pdf_path = os.path.join("temp_files", TEST_PDF)
        
        c = canvas.Canvas(pdf_path, pagesize=A4)
        c.drawString(100, 750, "纸盘设置测试")
        c.drawString(100, 700, f"打印机: {PRINTER_NAME}")
        c.drawString(100, 650, f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, 600, "如果您看到这个文档，说明纸盘设置成功！")
        c.save()
        
        logger.info(f"✅ 测试PDF已创建: {pdf_path}")
        return pdf_path
        
    except ImportError:
        logger.error("❌ 需要安装 reportlab: pip install reportlab")
        return None
    except Exception as e:
        logger.error(f"❌ 创建PDF失败: {e}")
        return None

def check_printer_trays():
    """检查打印机支持的纸盘"""
    logger.info("🔍 检查打印机纸盘信息...")
    
    try:
        # 方法1: 使用lpoptions查看
        result = subprocess.run(
            ['lpoptions', '-p', PRINTER_NAME, '-l'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ lpoptions检查成功")
            logger.info("纸盘选项:")
            for line in result.stdout.split('\n'):
                if 'media-source' in line or 'tray' in line:
                    logger.info(f"  {line.strip()}")
        else:
            logger.warning(f"⚠️ lpoptions检查失败: {result.stderr}")
        
        # 方法2: 使用lpstat查看
        result2 = subprocess.run(
            ['lpstat', '-p', PRINTER_NAME, '-l'], 
            capture_output=True, 
            text=True
        )
        
        if result2.returncode == 0:
            logger.info("✅ lpstat检查成功")
            logger.info("打印机详细信息:")
            logger.info(result2.stdout)
        else:
            logger.warning(f"⚠️ lpstat检查失败: {result2.stderr}")
            
    except Exception as e:
        logger.error(f"❌ 检查纸盘信息失败: {e}")

def test_print_with_tray(tray_name, method="lp"):
    """测试使用指定纸盘打印"""
    logger.info(f"🧪 测试使用纸盘 {tray_name} 打印 (方法: {method})")
    
    pdf_path = create_test_pdf()
    if not pdf_path:
        return False
    
    try:
        if method == "lp":
            # 使用lp命令
            cmd = [
                'lp', 
                '-d', PRINTER_NAME,
                '-o', f'media-source={tray_name}',
                pdf_path
            ]
        elif method == "lpr":
            # 使用lpr命令
            cmd = [
                'lpr', 
                '-P', PRINTER_NAME,
                '-o', f'media-source={tray_name}',
                pdf_path
            ]
        else:
            logger.error(f"❌ 不支持的打印方法: {method}")
            return False
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        # 执行打印
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info(f"✅ 使用纸盘 {tray_name} 打印成功")
            if result.stdout:
                logger.info(f"输出: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ 使用纸盘 {tray_name} 打印失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ 打印命令执行超时")
        return False
    except Exception as e:
        logger.error(f"❌ 打印异常: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"🧹 已清理测试文件")
        except:
            pass

def test_print_without_tray():
    """测试不指定纸盘打印（使用打印机默认设置）"""
    logger.info("🧪 测试不指定纸盘打印（使用打印机默认设置）")
    
    pdf_path = create_test_pdf()
    if not pdf_path:
        return False
    
    try:
        # 使用lp命令，不指定纸盘
        cmd = ['lp', '-d', PRINTER_NAME, pdf_path]
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✅ 不指定纸盘打印成功（使用默认设置）")
            if result.stdout:
                logger.info(f"输出: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ 不指定纸盘打印失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ 打印命令执行超时")
        return False
    except Exception as e:
        logger.error(f"❌ 打印异常: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
                logger.info(f"🧹 已清理测试文件")
        except:
            pass

def test_different_tray_names():
    """测试不同的纸盘名称"""
    logger.info("🧪 测试不同的纸盘名称...")
    
    # 根据您的打印机实际支持的纸盘名称
    tray_names = [
        "auto", "top", "bottom", "multi", "by-pass-tray"
    ]
    
    successful_trays = []
    
    for tray_name in tray_names:
        logger.info(f"📋 测试纸盘名称: {tray_name}")
        if test_print_with_tray(tray_name):
            successful_trays.append(tray_name)
        time.sleep(1)  # 间隔时间
    
    if successful_trays:
        logger.info(f"🎉 成功的纸盘名称: {', '.join(successful_trays)}")
    else:
        logger.warning("⚠️ 没有找到成功的纸盘名称")

def main():
    """主函数"""
    print("🖨️  纸盘设置测试工具")
    print("=" * 40)
    
    # 检查打印机状态
    logger.info(f"🔍 检查打印机: {PRINTER_NAME}")
    
    # 检查打印机是否存在
    result = subprocess.run(['lpstat', '-p', PRINTER_NAME], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"❌ 打印机 {PRINTER_NAME} 不存在或不可访问")
        logger.error(f"错误信息: {result.stderr}")
        return
    
    logger.info(f"✅ 打印机 {PRINTER_NAME} 存在")
    
    # 检查纸盘信息
    check_printer_trays()
    print()
    
    # 测试不同的纸盘名称
    logger.info("🚀 开始测试纸盘设置...")
    test_different_tray_names()
    print()
    
    # 测试不指定纸盘
    logger.info("🚀 测试不指定纸盘（默认设置）...")
    test_print_without_tray()
    print()
    
    logger.info("🏁 测试完成！")
    logger.info("💡 建议：")
    logger.info("1. 查看上面的测试结果，找到成功的纸盘名称")
    logger.info("2. 如果所有纸盘名称都失败，使用不指定纸盘的方法")
    logger.info("3. 根据测试结果修改您的打印代码")

if __name__ == "__main__":
    main()
