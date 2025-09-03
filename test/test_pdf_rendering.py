#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF渲染测试工具
验证PDF是否正确渲染和打印
"""

import os
import tempfile
import subprocess
from datetime import datetime


def create_test_pdf():
    """创建测试PDF文件"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        # 创建临时PDF文件
        file_path = os.path.join(tempfile.gettempdir(), f"test_pdf_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        c = canvas.Canvas(file_path, pagesize=A4)
        c.setFont('Helvetica', 14)
        
        # 添加测试内容
        y_position = 750
        
        c.drawString(100, y_position, "PDF Rendering Test")
        y_position -= 30
        
        c.drawString(100, y_position, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        y_position -= 30
        
        c.drawString(100, y_position, "This is a test PDF file.")
        y_position -= 25
        
        c.drawString(100, y_position, "If you can see this properly formatted, PDF rendering works!")
        y_position -= 25
        
        c.drawString(100, y_position, "=" * 50)
        y_position -= 30
        
        c.drawString(100, y_position, "Test Content:")
        y_position -= 25
        
        test_lines = [
            "Line 1: Basic text",
            "Line 2: Numbers 1234567890",
            "Line 3: Symbols !@#$%^&*()",
            "Line 4: Special chars &lt;&gt;&amp;",
            "Line 5: Chinese test: 你好世界",
        ]
        
        for line in test_lines:
            c.drawString(120, y_position, line)
            y_position -= 20
        
        c.save()
        
        print(f"✅ 测试PDF已创建: {file_path}")
        return file_path
        
    except ImportError:
        print("❌ 缺少reportlab库")
        return None
    except Exception as e:
        print(f"❌ 创建PDF失败: {e}")
        return None


def test_pdf_rendering(pdf_file):
    """测试PDF渲染"""
    print(f"\n测试PDF渲染: {pdf_file}")
    
    # 检查PDF文件信息
    try:
        result = subprocess.run(['file', pdf_file], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"文件类型: {result.stdout.strip()}")
    except:
        pass
    
    # 使用pdftops转换测试
    try:
        ps_file = pdf_file.replace('.pdf', '.ps')
        result = subprocess.run(['pdftops', pdf_file, ps_file], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PDF到PS转换成功")
            
            # 检查PS文件
            ps_size = os.path.getsize(ps_file)
            print(f"PS文件大小: {ps_size} bytes")
            
            # 清理PS文件
            os.remove(ps_file)
        else:
            print(f"❌ PDF到PS转换失败: {result.stderr}")
    except Exception as e:
        print(f"❌ PDF转换测试失败: {e}")
    
    # 使用Ghostscript测试
    try:
        result = subprocess.run(['gs', '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=nullpage', pdf_file], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Ghostscript可以处理PDF")
        else:
            print(f"❌ Ghostscript处理失败: {result.stderr}")
    except Exception as e:
        print(f"❌ Ghostscript测试失败: {e}")


def test_print_methods(pdf_file, printer_name="HP_Printer_40"):
    """测试不同的打印方法"""
    print(f"\n测试打印方法: {printer_name}")
    
    methods = [
        ("lpr", ["lpr", "-P", printer_name, pdf_file]),
        ("pdftops", ["pdftops", pdf_file, "-", "|", "lpr", "-P", printer_name]),
    ]
    
    for method_name, cmd in methods:
        print(f"\n测试方法: {method_name}")
        print(f"命令: {' '.join(cmd)}")
        
        try:
            if method_name == "lpr":
                result = subprocess.run(cmd, capture_output=True, text=True)
            elif method_name == "pdftops":
                # 使用管道
                ps_process = subprocess.Popen(['pdftops', pdf_file, '-'], stdout=subprocess.PIPE)
                lpr_process = subprocess.Popen(['lpr', '-P', printer_name], stdin=ps_process.stdout)
                ps_process.stdout.close()
                result = lpr_process.communicate()
                result = type('Result', (), {'returncode': lpr_process.returncode, 'stderr': result[1]})()
            
            if result.returncode == 0:
                print(f"✅ {method_name} 打印成功")
            else:
                print(f"❌ {method_name} 打印失败: {result.stderr}")
                
        except Exception as e:
            print(f"❌ {method_name} 测试异常: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("PDF渲染和打印测试工具")
    print("=" * 60)
    
    # 1. 创建测试PDF
    print("\n1. 创建测试PDF文件...")
    pdf_file = create_test_pdf()
    
    if not pdf_file:
        print("❌ 无法创建测试PDF")
        return
    
    # 2. 测试PDF渲染
    print("\n2. 测试PDF渲染...")
    test_pdf_rendering(pdf_file)
    
    # 3. 获取打印机列表
    print("\n3. 获取打印机列表...")
    try:
        result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
        if result.returncode == 0:
            printers = []
            for line in result.stdout.strip().split('\n'):
                if line.startswith('打印机 '):
                    parts = line.split()
                    if len(parts) >= 2:
                        printers.append(parts[1])
            
            if printers:
                print(f"找到打印机: {printers}")
                
                # 4. 测试打印方法
                print(f"\n4. 测试打印方法...")
                # 优先使用HP_Printer_40，如果不存在则使用第一个可用打印机
                target_printer = "HP_Printer_40"
                if target_printer in printers:
                    print(f"✅ 使用指定打印机: {target_printer}")
                    test_print_methods(pdf_file, target_printer)
                else:
                    print(f"⚠️ 未找到 {target_printer}，使用第一个可用打印机: {printers[0]}")
                    test_print_methods(pdf_file, printers[0])
            else:
                print("❌ 未找到可用打印机")
        else:
            print("❌ 获取打印机列表失败")
    except Exception as e:
        print(f"❌ 打印机测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
