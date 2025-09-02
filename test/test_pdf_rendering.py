#!/usr/bin/env python3
"""
PDF渲染测试工具
测试不同打印方法的PDF渲染效果
"""

import os
import sys
import requests
import tempfile
import subprocess

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.config_service import ConfigService


def create_test_pdf():
    """创建一个简单的测试PDF文件"""
    test_pdf = "test_pdf_rendering.pdf"
    
    # 使用Python创建简单的PDF
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(test_pdf, pagesize=letter)
        c.drawString(100, 750, "PDF渲染测试")
        c.drawString(100, 730, "这是一个测试PDF文件")
        c.drawString(100, 710, "用于验证PDF渲染是否正确")
        c.drawString(100, 690, "如果打印出来是乱码，说明渲染有问题")
        c.drawString(100, 670, "如果打印出来正常，说明渲染正确")
        c.drawString(100, 650, "测试时间: 2025-08-22")
        c.save()
        
        print(f"✅ 创建测试PDF文件: {test_pdf}")
        return test_pdf
    except ImportError:
        print("❌ 未安装reportlab，无法创建测试PDF")
        return None


def test_print_method(method, printer_name="HP-LaserJet-MFP-M437-M443"):
    """测试指定的打印方法"""
    print(f"\n{'='*50}")
    print(f"测试打印方法: {method}")
    print(f"{'='*50}")
    
    # 创建测试PDF
    test_pdf = create_test_pdf()
    if not test_pdf:
        return False
    
    try:
        # 获取API配置
        api_url = ConfigService.get_print_api_url('print')
        headers = ConfigService.get_auth_headers()
        
        # 发送打印请求
        with open(test_pdf, 'rb') as pdf_file:
            files = {'file': (test_pdf, pdf_file, 'application/pdf')}
            response = requests.post(
                f"{api_url}?printer_name={printer_name}&method={method}",
                headers=headers,
                files=files
            )
        
        print(f"API请求URL: {api_url}?printer_name={printer_name}&method={method}")
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ {method} 方法打印成功")
                print(f"   任务ID: {data.get('job_id')}")
                return True
            else:
                print(f"❌ {method} 方法打印失败")
                print(f"   错误信息: {data.get('message')}")
                return False
        else:
            print(f"❌ API请求失败")
            print(f"   响应内容: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 测试 {method} 方法时出错: {str(e)}")
        return False
    finally:
        # 清理测试文件
        if os.path.exists(test_pdf):
            os.remove(test_pdf)


def test_system_tools():
    """测试系统PDF工具"""
    print(f"\n{'='*50}")
    print("测试系统PDF工具")
    print(f"{'='*50}")
    
    tools = {
        'pdftops': 'PDF到PostScript转换',
        'gs': 'Ghostscript PDF处理',
        'lpr': 'CUPS打印系统'
    }
    
    for tool, description in tools.items():
        result = subprocess.run(['which', tool], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {tool}: {description}")
            # 获取版本信息
            try:
                version_result = subprocess.run([tool, '--version'], capture_output=True, text=True, timeout=5)
                if version_result.returncode == 0:
                    version_line = version_result.stdout.strip().split('\n')[0]
                    print(f"   版本: {version_line}")
            except:
                pass
        else:
            print(f"❌ {tool}: 未安装")


def test_pdf_conversion():
    """测试PDF转换功能"""
    print(f"\n{'='*50}")
    print("测试PDF转换功能")
    print(f"{'='*50}")
    
    # 创建测试PDF
    test_pdf = create_test_pdf()
    if not test_pdf:
        return
    
    try:
        # 测试pdftops转换
        ps_file = test_pdf.replace('.pdf', '.ps')
        result = subprocess.run(['pdftops', test_pdf, ps_file], capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(ps_file):
            print(f"✅ PDF到PS转换成功: {ps_file}")
            # 检查PS文件内容
            with open(ps_file, 'r') as f:
                content = f.read(500)
                if 'PDF渲染测试' in content or 'test' in content.lower():
                    print("✅ PS文件内容正确")
                else:
                    print("⚠️  PS文件内容可能有问题")
        else:
            print(f"❌ PDF到PS转换失败: {result.stderr}")
        
        # 清理PS文件
        if os.path.exists(ps_file):
            os.remove(ps_file)
            
    except Exception as e:
        print(f"❌ PDF转换测试出错: {str(e)}")
    finally:
        # 清理测试PDF
        if os.path.exists(test_pdf):
            os.remove(test_pdf)


def main():
    """主测试函数"""
    print("PDF渲染测试工具")
    print("=" * 50)
    
    # 测试系统工具
    test_system_tools()
    
    # 测试PDF转换
    test_pdf_conversion()
    
    # 测试不同打印方法
    methods = ['lpr', 'pdftops', 'ghostscript']
    
    print(f"\n{'='*50}")
    print("开始测试打印方法")
    print(f"{'='*50}")
    
    results = {}
    for method in methods:
        results[method] = test_print_method(method)
    
    # 总结
    print(f"\n{'='*50}")
    print("测试结果总结")
    print(f"{'='*50}")
    
    for method, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{method}: {status}")
    
    print(f"\n建议:")
    if results.get('pdftops'):
        print("✅ 推荐使用 pdftops 方法，它提供最好的PDF渲染")
    elif results.get('ghostscript'):
        print("✅ 可以使用 ghostscript 方法作为备选")
    elif results.get('lpr'):
        print("⚠️  lpr 方法可能无法正确渲染PDF，建议使用其他方法")
    else:
        print("❌ 所有方法都失败了，请检查系统配置")


if __name__ == "__main__":
    main()
