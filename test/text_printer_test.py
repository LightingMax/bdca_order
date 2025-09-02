#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本打印测试工具
用于测试文本打印功能，将内容打印到文本文件
"""

import os
import tempfile
import subprocess
import platform
from datetime import datetime


class TextPrinter:
    """文本打印器"""
    
    def __init__(self):
        self.system = platform.system().lower()
    
    def print_to_file(self, content, output_file=None):
        """将内容打印到文件"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"print_test_{timestamp}.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 内容已打印到文件: {output_file}")
            print(f"文件路径: {os.path.abspath(output_file)}")
            return output_file
        except Exception as e:
            print(f"❌ 打印到文件失败: {e}")
            return None
    
    def print_to_console(self, content):
        """将内容打印到控制台"""
        print("=" * 50)
        print("打印内容:")
        print("=" * 50)
        print(content)
        print("=" * 50)
    
    def create_test_content(self, message="Hello World"):
        """创建测试内容"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""
{message}
====================
测试时间: {timestamp}
系统: {platform.system()} {platform.release()}
Python版本: {platform.python_version()}
====================
这是一个打印机测试文件。
用于验证打印功能是否正常工作。

如果您看到这个文件，说明打印功能正常！
        """.strip()
        return content
    
    def print_hello_world(self, output_file=None):
        """打印Hello World测试"""
        content = self.create_test_content("Hello World")
        
        # 打印到控制台
        self.print_to_console(content)
        
        # 打印到文件
        file_path = self.print_to_file(content, output_file)
        
        return file_path
    
    def print_custom_message(self, message, output_file=None):
        """打印自定义消息"""
        content = self.create_test_content(message)
        
        # 打印到控制台
        self.print_to_console(content)
        
        # 打印到文件
        file_path = self.print_to_file(content, output_file)
        
        return file_path
    
    def list_available_printers(self):
        """列出可用的打印机（系统命令）"""
        try:
            if self.system == "linux":
                # 使用lpstat命令列出打印机
                result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ 系统打印机列表:")
                    print(result.stdout)
                    return result.stdout
                else:
                    print("❌ 获取打印机列表失败")
                    return None
            elif self.system == "windows":
                # 使用wmic命令列出打印机
                result = subprocess.run(['wmic', 'printer', 'get', 'name'], capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ 系统打印机列表:")
                    print(result.stdout)
                    return result.stdout
                else:
                    print("❌ 获取打印机列表失败")
                    return None
            else:
                print(f"❌ 不支持的操作系统: {self.system}")
                return None
        except Exception as e:
            print(f"❌ 获取打印机列表异常: {e}")
            return None
    
    def print_to_system_printer(self, content, printer_name=None):
        """使用系统打印机打印内容"""
        try:
            # 先创建临时文件
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            temp_file.write(content)
            temp_file.close()
            
            if self.system == "linux":
                # 使用lpr命令打印
                cmd = ['lpr']
                if printer_name:
                    cmd.extend(['-P', printer_name])
                cmd.append(temp_file.name)
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ 文件已发送到打印机: {temp_file.name}")
                    return True
                else:
                    print(f"❌ 打印失败: {result.stderr}")
                    return False
                    
            elif self.system == "windows":
                # 使用print命令打印
                cmd = ['print']
                if printer_name:
                    cmd.extend(['/d:', printer_name])
                cmd.append(temp_file.name)
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ 文件已发送到打印机: {temp_file.name}")
                    return True
                else:
                    print(f"❌ 打印失败: {result.stderr}")
                    return False
            else:
                print(f"❌ 不支持的操作系统: {self.system}")
                return False
                
        except Exception as e:
            print(f"❌ 系统打印异常: {e}")
            return False
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file.name)
            except:
                pass

    def create_test_pdf(self, content="Hello World", filename="test.pdf"):
        """创建测试PDF文件"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.units import inch
            
            file_path = os.path.join(tempfile.gettempdir(), filename)
            c = canvas.Canvas(file_path, pagesize=A4)
            
            # 尝试注册中文字体
            try:
                # 尝试使用系统字体
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/System/Library/Fonts/Arial.ttf',  # macOS
                    'C:/Windows/Fonts/arial.ttf',  # Windows
                ]
                
                font_registered = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                            font_registered = True
                            break
                        except:
                            continue
                
                if font_registered:
                    c.setFont('ChineseFont', 12)
                else:
                    # 使用默认字体
                    c.setFont('Helvetica', 12)
            except:
                # 如果字体注册失败，使用默认字体
                c.setFont('Helvetica', 12)
            
            # 设置页面尺寸（A4）
            page_width, page_height = A4
            
            # 添加内容
            y_position = page_height - 100
            
            # 标题
            c.drawString(100, y_position, content)
            y_position -= 30
            
            # 时间戳（英文避免编码问题）
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.drawString(100, y_position, f"Test Time: {timestamp}")
            y_position -= 30
            
            # 系统信息
            c.drawString(100, y_position, f"System: {platform.system()} {platform.release()}")
            y_position -= 30
            
            c.drawString(100, y_position, f"Python Version: {platform.python_version()}")
            y_position -= 30
            
            # 分隔线
            c.drawString(100, y_position, "=" * 50)
            y_position -= 30
            
            # 说明文字
            c.drawString(100, y_position, "This is a printer test file.")
            y_position -= 20
            c.drawString(100, y_position, "If you can see this file, the printer is working!")
            y_position -= 20
            
            # 中文测试（如果字体支持）
            if font_registered:
                c.drawString(100, y_position, "这是一个打印机测试文件。")
                y_position -= 20
                c.drawString(100, y_position, "如果您看到这个文件，说明打印功能正常！")
            
            c.save()
            
            print(f"✅ 测试PDF文件已创建: {file_path}")
            return file_path
        except ImportError:
            print("❌ 缺少reportlab库，请安装: pip install reportlab")
            return None
        except Exception as e:
            print(f"❌ 创建PDF文件失败: {e}")
            return None


def main():
    """主函数"""
    printer = TextPrinter()
    
    print("=" * 50)
    print("文本打印测试工具")
    print("=" * 50)
    
    # 1. 列出系统打印机
    print("\n1. 获取系统打印机列表:")
    printer.list_available_printers()
    
    print("\n" + "-" * 30)
    
    # 2. 打印Hello World到文件
    print("\n2. 打印Hello World到文件:")
    file_path = printer.print_hello_world()
    
    print("\n" + "-" * 30)
    
    # 3. 打印自定义消息
    print("\n3. 打印自定义消息:")
    custom_file = printer.print_custom_message("这是自定义测试消息！")
    
    print("\n" + "-" * 30)
    
    # 4. 尝试系统打印（可选）
    print("\n4. 尝试系统打印:")
    content = printer.create_test_content("系统打印测试")
    printer.print_to_system_printer(content)
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
