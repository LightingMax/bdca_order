#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动PDF拼接测试脚本
测试两个具体PDF文件的拼接效果
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def test_pdftk_combine():
    """使用pdftk测试拼接"""
    print("🔧 使用pdftk测试拼接...")
    
    # 文件路径
    invoice_path = "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子发票.pdf"
    itinerary_path = "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    output_path = "temp_files/test_combined_pdftk.pdf"
    
    if not os.path.exists(invoice_path):
        print(f"❌ 发票文件不存在: {invoice_path}")
        return False
    
    if not os.path.exists(itinerary_path):
        print(f"❌ 行程单文件不存在: {itinerary_path}")
        return False
    
    try:
        # 使用pdftk cat进行垂直拼接
        print("🔄 使用pdftk cat进行垂直拼接...")
        subprocess.run([
            'pdftk', invoice_path, itinerary_path, 
            'cat', 'output', output_path
        ], check=True)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ pdftk拼接成功: {output_path}")
            print(f"   文件大小: {file_size} bytes")
            
            # 验证拼接结果
            result = subprocess.run(['pdftk', output_path, 'dump_data'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('NumberOfPages:'):
                        page_count = int(line.split(':')[1].strip())
                        print(f"   页数: {page_count}")
                        break
            
            return True
        else:
            print("❌ 拼接文件未生成")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ pdftk拼接失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 拼接过程出错: {e}")
        return False

def test_pdftk_stamp():
    """使用pdftk stamp测试拼接"""
    print("\n🔧 使用pdftk stamp测试拼接...")
    
    # 文件路径
    invoice_path = "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子发票.pdf"
    itinerary_path = "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    output_path = "temp_files/test_combined_stamp.pdf"
    
    try:
        # 使用pdftk stamp进行盖印拼接
        print("🔄 使用pdftk stamp进行盖印拼接...")
        subprocess.run([
            'pdftk', invoice_path, 
            'stamp', itinerary_path, 
            'output', output_path
        ], check=True)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ pdftk stamp拼接成功: {output_path}")
            print(f"   文件大小: {file_size} bytes")
            
            # 验证拼接结果
            result = subprocess.run(['pdftk', output_path, 'dump_data'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('NumberOfPages:'):
                        page_count = int(line.split(':')[1].strip())
                        print(f"   页数: {page_count}")
                        break
            
            return True
        else:
            print("❌ 拼接文件未生成")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ pdftk stamp拼接失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 拼接过程出错: {e}")
        return False

def test_pypdf2_combine():
    """使用PyPDF2测试拼接"""
    print("\n📚 使用PyPDF2测试拼接...")
    
    try:
        import PyPDF2
        print("✅ PyPDF2库可用")
    except ImportError:
        print("❌ PyPDF2库不可用，跳过测试")
        return False
    
    # 文件路径
    invoice_path = "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子发票.pdf"
    itinerary_path = "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    output_path = "temp_files/test_combined_pypdf2.pdf"
    
    try:
        # 读取发票文件
        with open(invoice_path, 'rb') as invoice_file:
            invoice_reader = PyPDF2.PdfReader(invoice_file)
            invoice_page = invoice_reader.pages[0]
            print(f"🧾 发票页数: {len(invoice_reader.pages)}")
        
        # 读取行程单文件
        with open(itinerary_path, 'rb') as itinerary_file:
            itinerary_reader = PyPDF2.PdfReader(itinerary_file)
            itinerary_page = itinerary_reader.pages[0]
            print(f"📄 行程单页数: {len(itinerary_reader.pages)}")
        
        # 创建新的PDF
        writer = PyPDF2.PdfWriter()
        
        # 添加发票页面
        writer.add_page(invoice_page)
        
        # 添加行程单第一页
        writer.add_page(itinerary_page)
        
        # 保存拼接后的PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ PyPDF2拼接成功: {output_path}")
            print(f"   文件大小: {file_size} bytes")
            print(f"   页数: {len(writer.pages)}")
            return True
        else:
            print("❌ 拼接文件未生成")
            return False
            
    except Exception as e:
        print(f"❌ PyPDF2拼接失败: {e}")
        return False

def test_page_extraction():
    """测试页面提取"""
    print("\n📄 测试页面提取...")
    
    # 文件路径
    itinerary_path = "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    
    try:
        # 提取第一页
        first_page_path = "temp_files/itinerary_first_page.pdf"
        subprocess.run(['pdftk', itinerary_path, 'cat', '1', 'output', first_page_path], check=True)
        
        if os.path.exists(first_page_path):
            file_size = os.path.getsize(first_page_path)
            print(f"✅ 第一页提取成功: {first_page_path}")
            print(f"   文件大小: {file_size} bytes")
        
        # 提取第二页
        second_page_path = "temp_files/itinerary_second_page.pdf"
        subprocess.run(['pdftk', itinerary_path, 'cat', '2', 'output', second_page_path], check=True)
        
        if os.path.exists(second_page_path):
            file_size = os.path.getsize(second_page_path)
            print(f"✅ 第二页提取成功: {second_page_path}")
            print(f"   文件大小: {file_size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ 页面提取失败: {e}")
        return False

def analyze_pdf_files():
    """分析PDF文件信息"""
    print("\n🔍 分析PDF文件信息...")
    
    files = [
        "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子发票.pdf",
        "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    ]
    
    for file_path in files:
        if os.path.exists(file_path):
            try:
                result = subprocess.run(['pdftk', file_path, 'dump_data'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    page_count = 0
                    page_size = None
                    
                    for line in result.stdout.split('\n'):
                        if line.startswith('NumberOfPages:'):
                            page_count = int(line.split(':')[1].strip())
                        elif line.startswith('PageMediaDimensions:'):
                            page_size = line.split(':')[1].strip()
                    
                    file_size = os.path.getsize(file_path)
                    print(f"📋 {os.path.basename(file_path)}:")
                    print(f"   页数: {page_count}")
                    print(f"   尺寸: {page_size}")
                    print(f"   大小: {file_size} bytes")
                else:
                    print(f"❌ 无法读取文件信息: {file_path}")
            except Exception as e:
                print(f"❌ 分析文件失败: {file_path} - {e}")
        else:
            print(f"❌ 文件不存在: {file_path}")

def main():
    """主函数"""
    print("🧪 PDF拼接测试工具")
    print("=" * 60)
    
    # 检查pdftk工具
    if not shutil.which('pdftk'):
        print("❌ pdftk工具不可用，请先安装")
        return False
    
    # 分析原始文件
    analyze_pdf_files()
    
    # 测试不同的拼接方法
    tests = [
        test_pdftk_combine,
        test_pdftk_stamp,
        test_pypdf2_combine,
        test_page_extraction
    ]
    
    success_count = 0
    for test in tests:
        try:
            if test():
                success_count += 1
        except Exception as e:
            print(f"❌ 测试 {test.__name__} 失败: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {success_count}/{len(tests)} 通过")
    
    if success_count == len(tests):
        print("🎉 所有拼接测试完成！")
        print("\n💡 现在您可以：")
        print("   1. 查看生成的拼接文件")
        print("   2. 选择最佳的拼接方法")
        print("   3. 将方法集成到智能打印中")
    else:
        print("⚠️ 部分测试失败，请检查相关配置")
    
    return success_count == len(tests)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        sys.exit(1)
