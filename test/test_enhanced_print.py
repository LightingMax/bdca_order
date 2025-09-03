#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的打印功能
"""

import os
import sys
import tempfile
import requests
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_pdf():
    """创建测试PDF文件"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        file_path = tempfile.mktemp(suffix='.pdf')
        
        c = canvas.Canvas(file_path, pagesize=A4)
        c.setFont('Helvetica', 16)
        
        # 添加测试内容
        y_position = 750
        
        c.drawString(100, y_position, "ENHANCED PRINT TEST")
        c.drawString(100, y_position - 30, "=" * 40)
        c.drawString(100, y_position - 60, "This tests the enhanced Linux printing")
        c.drawString(100, y_position - 90, "Multiple methods will be tried")
        c.drawString(100, y_position - 120, "Time: " + time.strftime("%Y-%m-%d %H:%M:%S"))
        
        c.save()
        
        print(f"✅ 测试PDF已创建: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"❌ 创建PDF失败: {e}")
        return None

def test_print_methods():
    """测试不同的打印方法"""
    print("🧪 测试不同的打印方法...")
    
    pdf_path = create_test_pdf()
    if not pdf_path:
        return False
    
    try:
        # 打印API配置
        api_url = "http://localhost:12346/print"
        api_token = "TOKEN_PRINT_API_KEY_9527"
        printer_name = "HP-LaserJet-MFP-M437-M443"
        
        headers = {
            "Authorization": f"Bearer {api_token}"
        }
        
        # 测试CUPS打印方法
        methods = ["cups"]
        
        for method in methods:
            print(f"\n📋 测试方法: {method}")
            
            params = {
                "printer_name": printer_name,
                "copies": 1,
                "method": method
            }
            
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    files = {'file': ('test.pdf', pdf_file, 'application/pdf')}
                    
                    response = requests.post(api_url, headers=headers, params=params, files=files)
                
                print(f"  状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print(f"  ✅ {method} 方法成功")
                        print(f"     任务ID: {data.get('job_id')}")
                        
                        # 等待几秒，检查打印队列
                        time.sleep(3)
                        check_print_queue()
                        
                        # 如果成功，就不需要测试其他方法了
                        if method != "auto":
                            break
                    else:
                        print(f"  ❌ {method} 方法失败: {data.get('message')}")
                else:
                    print(f"  ❌ {method} 方法请求失败: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ {method} 方法异常: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            os.remove(pdf_path)
        except:
            pass

def check_print_queue():
    """检查打印队列状态"""
    print("  📊 检查打印队列:")
    
    try:
        import subprocess
        
        # 检查打印机状态
        result = subprocess.run(['lpstat', '-p', 'HP-LaserJet-MFP-M437-M443', '-l'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    打印机状态: {result.stdout.strip()}")
        
        # 检查打印队列
        result = subprocess.run(['lpq', '-P', 'HP-LaserJet-MFP-M437-M443'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    队列状态: {result.stdout.strip()}")
            
    except Exception as e:
        print(f"    检查队列失败: {e}")

def test_printer_status():
    """测试打印机状态API"""
    print("\n🖨️  测试打印机状态API...")
    
    try:
        api_url = "http://localhost:12346/printer-status/HP_LaserJet_MFP_M437_M443_NPIDC0D3D_"
        api_token = "TOKEN_PRINT_API_KEY_9527"
        
        headers = {
            "Authorization": f"Bearer {api_token}"
        }
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                printer_info = data
                print(f"✅ 打印机状态: {printer_info.get('state_text')}")
                print(f"   接受任务: {'✅' if printer_info.get('is_accepting') else '❌'}")
                print(f"   驱动: {printer_info.get('driver', 'Unknown')}")
                return True
            else:
                print(f"❌ 获取状态失败: {data.get('message')}")
                return False
        else:
            print(f"❌ 状态请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 状态测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🖨️  增强打印功能测试工具")
    print("=" * 50)
    
    # 测试打印机状态
    status_ok = test_printer_status()
    
    if status_ok:
        # 测试打印功能
        print_ok = test_print_methods()
        
        if print_ok:
            print("\n🎉 测试完成！")
            print("\n💡 建议:")
            print("1. 检查哪种打印方法最稳定")
            print("2. 观察打印队列状态")
            print("3. 验证实际打印输出")
        else:
            print("\n💥 打印测试失败！")
    else:
        print("\n⚠️  打印机状态异常，跳过打印测试")
