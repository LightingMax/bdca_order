#!/usr/bin/env python3
"""
打印机驱动测试工具
比较不同打印机的PDF处理能力
"""

import os
import sys
import subprocess
import tempfile

def create_simple_pdf():
    """创建一个简单的测试PDF"""
    test_pdf = "test_driver.pdf"
    
    # 使用echo和enscript创建简单的PDF
    try:
        # 创建文本文件
        with open("test.txt", "w", encoding="utf-8") as f:
            f.write("打印机驱动测试\n")
            f.write("这是一个测试文件\n")
            f.write("用于验证PDF渲染\n")
            f.write("测试时间: 2025-08-22\n")
        
        # 转换为PDF
        cmd = ['enscript', '-o', test_pdf, 'test.txt']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(test_pdf):
            print(f"✅ 创建测试PDF: {test_pdf}")
            # 清理文本文件
            os.remove("test.txt")
            return test_pdf
        else:
            print(f"❌ 创建PDF失败: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ 创建PDF出错: {e}")
        return None


def test_printer_driver(printer_name, test_pdf):
    """测试指定打印机的驱动能力"""
    print(f"\n{'='*60}")
    print(f"测试打印机: {printer_name}")
    print(f"{'='*60}")
    
    # 获取打印机详细信息
    print("打印机信息:")
    try:
        result = subprocess.run(['lpoptions', '-p', printer_name], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'printer-make-and-model' in line:
                    print(f"  驱动: {line}")
                elif 'device-uri' in line:
                    print(f"  设备: {line}")
        else:
            print(f"  无法获取打印机信息: {result.stderr}")
    except Exception as e:
        print(f"  获取打印机信息出错: {e}")
    
    # 测试直接打印PDF
    print(f"\n测试直接打印PDF:")
    try:
        cmd = ['lpr', '-P', printer_name, test_pdf]
        print(f"  命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("  ✅ 打印任务提交成功")
            return True
        else:
            print(f"  ❌ 打印失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ 打印出错: {e}")
        return False


def test_pdf_conversion_methods(printer_name, test_pdf):
    """测试不同的PDF转换方法"""
    print(f"\n测试PDF转换方法:")
    
    methods = [
        ('pdftops', ['pdftops', test_pdf, 'test.ps']),
        ('pdftotext', ['pdftotext', test_pdf, 'test.txt']),
        ('pdfinfo', ['pdfinfo', test_pdf])
    ]
    
    for method_name, cmd in methods:
        print(f"\n  {method_name}:")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"    ✅ {method_name} 成功")
                if method_name == 'pdfinfo':
                    print(f"    信息: {result.stdout.strip()[:100]}...")
            else:
                print(f"    ❌ {method_name} 失败: {result.stderr}")
        except Exception as e:
            print(f"    ❌ {method_name} 出错: {e}")
    
    # 清理临时文件
    for ext in ['.ps', '.txt']:
        temp_file = f"test{ext}"
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    """主测试函数"""
    print("打印机驱动测试工具")
    print("=" * 60)
    
    # 创建测试PDF
    test_pdf = create_simple_pdf()
    if not test_pdf:
        print("无法创建测试PDF，退出")
        return
    
    try:
        # 测试不同的打印机
        printers = [
            'HP_Printer_40',  # 原始打印机
            'HP_LaserJet_MFP_M437_M443_NPIDC0D3D_',  # 有驱动的打印机
            'NetworkPrinter'  # 另一个网络打印机
        ]
        
        results = {}
        for printer in printers:
            success = test_printer_driver(printer, test_pdf)
            results[printer] = success
            
            # 测试PDF转换方法
            test_pdf_conversion_methods(printer, test_pdf)
        
        # 总结
        print(f"\n{'='*60}")
        print("测试结果总结")
        print(f"{'='*60}")
        
        for printer, success in results.items():
            status = "✅ 成功" if success else "❌ 失败"
            print(f"{printer}: {status}")
        
        print(f"\n建议:")
        if results.get('HP_LaserJet_MFP_M437_M443_NPIDC0D3D_'):
            print("✅ 推荐使用 HP_LaserJet_MFP_M437_M443_NPIDC0D3D_")
            print("   它有完整的驱动程序，应该能正确处理PDF")
        elif results.get('NetworkPrinter'):
            print("✅ 可以尝试使用 NetworkPrinter")
        else:
            print("❌ 所有打印机都失败了，需要检查CUPS配置")
        
    finally:
        # 清理测试文件
        if os.path.exists(test_pdf):
            os.remove(test_pdf)


if __name__ == "__main__":
    main()
