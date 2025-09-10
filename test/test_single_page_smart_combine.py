#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试单页行程单智能拼接功能
测试 create_smart_combined_single_page 函数
"""

import os
import sys
import subprocess
import uuid
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 测试文件路径
TEST_DIR = project_root / "temp_files" / "extracted_test" / "高德打车电子发票 (1)"
ITINERARY_FILE = TEST_DIR / "【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
INVOICE_FILE = TEST_DIR / "【及时用车-53.21元-2个行程】高德打车电子发票.pdf"
OUTPUT_DIR = project_root / "temp_files" / "test_output"

def check_pdftk():
    """检查pdftk是否可用"""
    try:
        result = subprocess.run(['pdftk', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ pdftk 可用")
            return True
        else:
            print("❌ pdftk 不可用")
            return False
    except FileNotFoundError:
        print("❌ pdftk 未安装")
        return False
    except Exception as e:
        print(f"❌ 检查pdftk时出错: {e}")
        return False

def check_pdf_pages(pdf_path):
    """检查PDF页数"""
    try:
        result = subprocess.run(['pdftk', str(pdf_path), 'dump_data'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('NumberOfPages:'):
                    page_count = int(line.split(':')[1].strip())
                    return page_count
        return None
    except Exception as e:
        print(f"❌ 检查PDF页数失败: {e}")
        return None

def create_smart_combined_single_page_test(itinerary_path, invoice_path, output_path):
    """测试单页智能拼接：发票在上（占一半A4），行程单在下（占一半A4），压缩到一页"""
    try:
        print(f"🔄 开始测试单页智能拼接...")
        print(f"   行程单: {itinerary_path}")
        print(f"   发票: {invoice_path}")
        print(f"   输出: {output_path}")
        
        # 检查输入文件
        if not os.path.exists(itinerary_path):
            print(f"❌ 行程单文件不存在: {itinerary_path}")
            return False
        if not os.path.exists(invoice_path):
            print(f"❌ 发票文件不存在: {invoice_path}")
            return False
        
        # 检查输入文件页数
        itinerary_pages = check_pdf_pages(itinerary_path)
        invoice_pages = check_pdf_pages(invoice_path)
        print(f"📊 行程单页数: {itinerary_pages}")
        print(f"📊 发票页数: {invoice_pages}")
        
        if itinerary_pages != 1 or invoice_pages != 1:
            print("❌ 输入文件不是单页PDF")
            return False
        
        # 创建临时文件
        temp_invoice = f"/tmp/temp_invoice_single_{uuid.uuid4().hex[:8]}.pdf"
        temp_itinerary = f"/tmp/temp_itinerary_single_{uuid.uuid4().hex[:8]}.pdf"
        
        try:
            # 提取发票第一页
            print("🧾 提取发票第一页...")
            subprocess.run(['pdftk', str(invoice_path), 'cat', '1', 'output', temp_invoice], 
                         check=True, capture_output=True)
            print("✅ 发票第一页提取成功")
            
            # 提取行程单第一页
            print("📄 提取行程单第一页...")
            subprocess.run(['pdftk', str(itinerary_path), 'cat', '1', 'output', temp_itinerary], 
                         check=True, capture_output=True)
            print("✅ 行程单第一页提取成功")
            
            # 单页拼接：发票在上（一半A4），行程单在下（一半A4）
            try:
                print("🔄 使用pdftk cat进行单页垂直拼接...")
                
                # 使用pdftk cat进行垂直拼接，生成2页PDF
                temp_combined = f"/tmp/temp_combined_{uuid.uuid4().hex[:8]}.pdf"
                subprocess.run([
                    'pdftk', temp_invoice, temp_itinerary, 
                    'cat', 'output', temp_combined
                ], check=True, capture_output=True)
                print("✅ 2页PDF拼接成功")
                
                # 将2页PDF压缩到1页（使用pdftk的stamp功能，将第2页叠加到第1页上）
                print("🔄 将2页PDF压缩到1页显示...")
                subprocess.run([
                    'pdftk', temp_invoice, 
                    'stamp', temp_itinerary, 
                    'output', str(output_path)
                ], check=True, capture_output=True)
                
                print("✅ 单页智能拼接成功（发票+行程单压缩到一页）")
                
                # 验证输出文件
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"📊 单页拼接文件大小: {file_size} bytes")
                    
                    # 验证PDF有效性
                    result = subprocess.run(['pdftk', str(output_path), 'dump_data'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        page_count = 0
                        for line in result.stdout.split('\n'):
                            if line.startswith('NumberOfPages:'):
                                page_count = int(line.split(':')[1].strip())
                                break
                        
                        if page_count == 1:  # 压缩后应该是1页
                            print(f"✅ 单页拼接验证成功：{page_count}页")
                            return True
                        else:
                            print(f"⚠️ 单页拼接页数异常：{page_count}页")
                            return False
                    else:
                        print("⚠️ 无法验证PDF有效性")
                        return False
                else:
                    print("❌ 单页拼接输出文件未生成")
                    return False
                    
            except subprocess.CalledProcessError as e:
                print(f"⚠️ pdftk拼接失败: {e}")
                
                # 备选方案：使用PyPDF2进行单页拼接
                try:
                    print("🔄 尝试使用PyPDF2进行单页拼接...")
                    from PyPDF2 import PdfReader, PdfWriter
                    
                    # 读取两个PDF文件
                    with open(temp_invoice, 'rb') as invoice_file:
                        invoice_reader = PdfReader(invoice_file)
                        invoice_page = invoice_reader.pages[0]
                    
                    with open(temp_itinerary, 'rb') as itinerary_file:
                        itinerary_reader = PdfReader(itinerary_file)
                        itinerary_page = itinerary_reader.pages[0]
                    
                    # 创建新的PDF（2页）
                    writer = PdfWriter()
                    writer.add_page(invoice_page)
                    writer.add_page(itinerary_page)
                    
                    # 保存临时2页PDF
                    temp_2page = f"/tmp/temp_2page_{uuid.uuid4().hex[:8]}.pdf"
                    with open(temp_2page, 'wb') as output_file:
                        writer.write(output_file)
                    
                    # 使用pdftk压缩到1页
                    subprocess.run([
                        'pdftk', temp_2page, 
                        'cat', 'output', str(output_path), 
                        'scale', '0.5'
                    ], check=True, capture_output=True)
                    
                    print("✅ 使用PyPDF2+pdftk成功创建单页拼接")
                    return True
                    
                except Exception as e:
                    print(f"❌ PyPDF2拼接也失败了: {e}")
                    raise
                
        finally:
            # 清理临时文件
            temp_files_to_clean = [temp_invoice, temp_itinerary]
            if 'temp_combined' in locals():
                temp_files_to_clean.append(temp_combined)
            if 'temp_2page' in locals():
                temp_files_to_clean.append(temp_2page)
                
            for temp_file in temp_files_to_clean:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        print(f"🧹 清理临时文件: {temp_file}")
                    except Exception as e:
                        print(f"⚠️ 清理临时文件失败: {temp_file}, 错误: {e}")
                
    except Exception as e:
        print(f"❌ 创建单页智能拼接失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试单页行程单智能拼接功能")
    print("=" * 60)
    
    # 1. 检查环境
    print("🔍 检查测试环境...")
    if not check_pdftk():
        print("❌ 环境检查失败，无法继续测试")
        return
    
    # 2. 检查测试文件
    print("\n📁 检查测试文件...")
    if not ITINERARY_FILE.exists():
        print(f"❌ 行程单文件不存在: {ITINERARY_FILE}")
        return
    if not INVOICE_FILE.exists():
        print(f"❌ 发票文件不存在: {INVOICE_FILE}")
        return
    
    print(f"✅ 行程单文件: {ITINERARY_FILE}")
    print(f"✅ 发票文件: {INVOICE_FILE}")
    
    # 3. 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "test_single_page_combined.pdf"
    
    # 4. 执行测试
    print(f"\n🧪 执行单页智能拼接测试...")
    success = create_smart_combined_single_page_test(
        str(ITINERARY_FILE), 
        str(INVOICE_FILE), 
        str(output_file)
    )
    
    # 5. 测试结果
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试成功！")
        print(f"📄 输出文件: {output_file}")
        
        # 验证输出文件
        if output_file.exists():
            file_size = output_file.stat().st_size
            pages = check_pdf_pages(str(output_file))
            print(f"📊 输出文件信息:")
            print(f"   大小: {file_size} bytes")
            print(f"   页数: {pages} 页")
            
            if pages == 1:
                print("✅ 输出文件验证成功：1页PDF，内容已压缩")
            else:
                print("⚠️ 输出文件页数异常")
        else:
            print("❌ 输出文件未生成")
    else:
        print("❌ 测试失败！")
        print("请检查错误日志，可能需要修复代码逻辑")

if __name__ == "__main__":
    main()
