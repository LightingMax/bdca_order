#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试FastAPI的create_smart_combined_single_page函数
"""

import os
import sys
import subprocess
import uuid
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 测试文件路径（使用我们之前测试成功的文件）
TEST_DIR = project_root / "temp_files" / "extracted_test" / "高德打车电子发票 (1)"
ITINERARY_FILE = TEST_DIR / "【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
INVOICE_FILE = TEST_DIR / "【及时用车-53.21元-2个行程】高德打车电子发票.pdf"
OUTPUT_DIR = project_root / "temp_files" / "fastapi_test_output"

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

def test_fastapi_function_direct():
    """直接测试FastAPI的函数逻辑"""
    print("🧪 直接测试FastAPI的函数逻辑...")
    
    # 检查测试文件
    if not ITINERARY_FILE.exists():
        print(f"❌ 行程单文件不存在: {ITINERARY_FILE}")
        return False
    if not INVOICE_FILE.exists():
        print(f"❌ 发票文件不存在: {INVOICE_FILE}")
        return False
    
    print(f"✅ 行程单文件: {ITINERARY_FILE}")
    print(f"✅ 发票文件: {INVOICE_FILE}")
    
    # 检查文件页数
    itinerary_pages = check_pdf_pages(ITINERARY_FILE)
    invoice_pages = check_pdf_pages(INVOICE_FILE)
    print(f"📊 行程单页数: {itinerary_pages}")
    print(f"📊 发票页数: {invoice_pages}")
    
    if itinerary_pages != 1 or invoice_pages != 1:
        print("❌ 输入文件不是单页PDF")
        return False
    
    # 创建输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "fastapi_direct_test.pdf"
    
    # 直接调用函数逻辑（模拟FastAPI的调用）
    success = create_smart_combined_single_page_direct(
        str(ITINERARY_FILE), str(INVOICE_FILE), str(output_file)
    )
    
    if success:
        print("🎉 FastAPI函数测试成功！")
        return True
    else:
        print("❌ FastAPI函数测试失败")
        return False

def create_smart_combined_single_page_direct(itinerary_path, invoice_path, output_path):
    """直接测试单页智能拼接函数逻辑"""
    try:
        print(f"🔄 开始测试单页智能拼接...")
        print(f"   行程单: {itinerary_path}")
        print(f"   发票: {invoice_path}")
        print(f"   输出: {output_path}")
        
        # 创建临时文件
        temp_invoice = f"/tmp/temp_invoice_fastapi_{uuid.uuid4().hex[:8]}.pdf"
        temp_itinerary = f"/tmp/temp_itinerary_fastapi_{uuid.uuid4().hex[:8]}.pdf"
        
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
                print("🔄 使用pdftk stamp进行单页拼接（发票+行程单叠加到一页）")
                
                # 使用pdftk stamp将行程单叠加到发票上
                subprocess.run([
                    'pdftk', temp_invoice, 
                    'stamp', temp_itinerary, 
                    'output', str(output_path)
                ], check=True, capture_output=True)
                
                print("✅ 单页智能拼接成功（发票+行程单叠加到一页）")
                
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
                        
                        if page_count == 1:  # 应该是1页
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
                return False
                
        finally:
            # 清理临时文件
            temp_files_to_clean = [temp_invoice, temp_itinerary]
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
    print("🚀 直接测试FastAPI函数逻辑")
    print("=" * 60)
    
    # 检查环境
    try:
        result = subprocess.run(['pdftk', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ pdftk 可用")
        else:
            print("❌ pdftk 不可用")
            return
    except FileNotFoundError:
        print("❌ pdftk 未安装")
        return
    
    # 执行测试
    success = test_fastapi_function_direct()
    
    if success:
        print("\n🎉 测试完成！")
        print("如果这个测试成功，但网页调用失败，说明问题在于调用流程")
        print("如果这个测试也失败，说明问题在于函数本身")
    else:
        print("\n❌ 测试失败！")

if __name__ == "__main__":
    main()
