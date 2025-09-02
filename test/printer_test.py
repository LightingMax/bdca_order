#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印机测试工具
用于测试打印API服务的功能
"""

import requests
import os
import tempfile
import json
from datetime import datetime

# 打印API服务配置
PRINT_API_BASE_URL = "http://localhost:12346"
API_KEY = "TOKEN_PRINT_API_KEY_9527"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


class PrinterTester:
    """打印机测试类"""
    
    def __init__(self, base_url=PRINT_API_BASE_URL):
        self.base_url = base_url
        self.headers = HEADERS
    
    def test_connection(self):
        """测试API连接"""
        try:
            response = requests.get(f"{self.base_url}/printers", headers=self.headers)
            if response.status_code == 200:
                print("✅ API连接成功")
                return True
            else:
                print(f"❌ API连接失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API连接异常: {e}")
            return False
    
    def get_printers(self):
        """获取打印机列表"""
        try:
            response = requests.get(f"{self.base_url}/printers", headers=self.headers, timeout=10)
            if response.status_code == 200:
                # 检查响应内容是否为空
                if not response.text.strip():
                    print("❌ API返回空响应")
                    return []
                
                try:
                    data = response.json()
                    if data["success"]:
                        print(f"✅ 找到 {len(data['printers'])} 台打印机:")
                        for i, printer in enumerate(data['printers'], 1):
                            print(f"  {i}. {printer}")
                        return data['printers']
                    else:
                        print(f"❌ 获取打印机列表失败: {data['message']}")
                        return []
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    print(f"响应内容: {response.text[:200]}...")
                    return []
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}...")
                return []
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 连接错误: {e}")
            print("请确保打印API服务正在运行")
            return []
        except requests.exceptions.Timeout as e:
            print(f"❌ 请求超时: {e}")
            return []
        except Exception as e:
            print(f"❌ 获取打印机列表异常: {e}")
            return []
    
    def get_printers_detailed(self):
        """获取打印机详细信息"""
        try:
            response = requests.get(f"{self.base_url}/printers/detailed", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    print(f"✅ 打印机详细信息:")
                    for printer in data['printers']:
                        print(f"  名称: {printer['name']}")
                        print(f"  状态: {printer['state']}")
                        print(f"  信息: {printer['info']}")
                        print(f"  位置: {printer['location']}")
                        print("  ---")
                    return data['printers']
                else:
                    print(f"❌ 获取详细信息失败: {data['message']}")
                    return []
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 获取详细信息异常: {e}")
            return []
    
    def get_default_printer(self):
        """获取默认打印机"""
        try:
            response = requests.get(f"{self.base_url}/default-printer", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    print(f"✅ 默认打印机: {data['default_printer']}")
                    return data['default_printer']
                else:
                    print(f"❌ 获取默认打印机失败: {data['message']}")
                    return None
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 获取默认打印机异常: {e}")
            return None
    
    def get_printer_status(self, printer_name):
        """获取打印机状态"""
        try:
            response = requests.get(f"{self.base_url}/printer-status/{printer_name}", headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    print(f"✅ 打印机 {printer_name} 状态:")
                    print(f"  状态: {data['status']}")
                    print(f"  信息: {data['info']}")
                    return data
                else:
                    print(f"❌ 获取状态失败: {data['message']}")
                    return None
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 获取状态异常: {e}")
            return None
    
    def create_test_pdf(self, content="Hello World", filename="test.pdf"):
        """创建测试PDF文件"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            file_path = os.path.join(tempfile.gettempdir(), filename)
            c = canvas.Canvas(file_path, pagesize=letter)
            c.drawString(100, 750, content)
            c.drawString(100, 730, f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            c.save()
            
            print(f"✅ 测试PDF文件已创建: {file_path}")
            return file_path
        except ImportError:
            print("❌ 缺少reportlab库，请安装: pip install reportlab")
            return None
        except Exception as e:
            print(f"❌ 创建PDF文件失败: {e}")
            return None
    
    def print_test_file(self, printer_name, file_path, copies=1):
        """打印测试文件"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ 文件不存在: {file_path}")
                return False
            
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
                params = {'printer_name': printer_name, 'copies': copies}
                
                response = requests.post(
                    f"{self.base_url}/print",
                    headers=self.headers,
                    files=files,
                    params=params
                )
            
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    print(f"✅ 打印任务已提交，任务ID: {data['job_id']}")
                    return True
                else:
                    print(f"❌ 打印失败: {data['message']}")
                    return False
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 打印异常: {e}")
            return False
    
    def run_full_test(self):
        """运行完整测试"""
        print("=" * 50)
        print("开始打印机API测试")
        print("=" * 50)
        
        # 1. 测试连接
        if not self.test_connection():
            return False
        
        print("\n" + "-" * 30)
        
        # 2. 获取打印机列表
        printers = self.get_printers()
        if not printers:
            return False
        
        print("\n" + "-" * 30)
        
        # 3. 获取默认打印机
        default_printer = self.get_default_printer()
        
        print("\n" + "-" * 30)
        
        # 4. 创建测试PDF
        test_pdf = self.create_test_pdf("Hello World - 打印机测试")
        if not test_pdf:
            return False
        
        print("\n" + "-" * 30)
        
        # 5. 选择打印机进行测试
        if default_printer and default_printer in printers:
            test_printer = default_printer
            print(f"使用默认打印机进行测试: {test_printer}")
        elif printers:
            test_printer = printers[0]
            print(f"使用第一个可用打印机进行测试: {test_printer}")
        else:
            print("❌ 没有可用的打印机")
            return False
        
        # 6. 获取打印机状态
        self.get_printer_status(test_printer)
        
        print("\n" + "-" * 30)
        
        # 7. 执行打印测试
        success = self.print_test_file(test_printer, test_pdf, copies=1)
        
        print("\n" + "-" * 30)
        
        if success:
            print("✅ 完整测试通过")
        else:
            print("❌ 完整测试失败")
        
        return success


def main():
    """主函数"""
    tester = PrinterTester()
    
    # 运行完整测试
    tester.run_full_test()


if __name__ == "__main__":
    main()
