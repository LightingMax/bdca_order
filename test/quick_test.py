#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速打印机测试脚本
提供简单的测试选项
"""

import sys
import os

# 本脚本位于 test/ 下，与 printer_test.py 同级；不能用包名 `test.*`，会与 Python 标准库 test 冲突。
_test_dir = os.path.dirname(os.path.abspath(__file__))
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

from printer_test import PrinterTester
from text_printer_test import TextPrinter


def show_menu():
    """显示测试菜单"""
    print("\n" + "=" * 50)
    print("打印机测试工具")
    print("=" * 50)
    print("1. 测试打印API服务")
    print("2. 打印Hello World到文件")
    print("3. 打印自定义消息到文件")
    print("4. 获取系统打印机列表")
    print("5. 运行完整测试")
    print("0. 退出")
    print("=" * 50)


def test_print_api():
    """测试打印API服务"""
    print("\n开始测试打印API服务...")
    tester = PrinterTester()
    tester.run_full_test()


def test_text_print():
    """测试文本打印"""
    print("\n开始测试文本打印...")
    printer = TextPrinter()
    printer.print_hello_world()


def test_custom_message():
    """测试自定义消息打印"""
    message = input("\n请输入要打印的消息 (默认: Hello World): ").strip()
    if not message:
        message = "Hello World"
    
    print(f"\n开始打印自定义消息: {message}")
    printer = TextPrinter()
    printer.print_custom_message(message)


def list_system_printers():
    """列出系统打印机"""
    print("\n获取系统打印机列表...")
    printer = TextPrinter()
    printer.list_available_printers()


def run_full_test():
    """运行完整测试"""
    print("\n开始运行完整测试...")
    
    # 1. 测试文本打印
    print("\n" + "-" * 30)
    print("1. 测试文本打印功能")
    text_printer = TextPrinter()
    text_printer.print_hello_world()
    
    # 2. 测试打印API（如果服务运行）
    print("\n" + "-" * 30)
    print("2. 测试打印API服务")
    print("注意: 请确保打印API服务正在运行 (python print_api_service_linux_enhanced.py)")
    
    api_tester = PrinterTester()
    if api_tester.test_connection():
        api_tester.run_full_test()
    else:
        print("❌ 打印API服务未运行，请先启动服务")


def main():
    """主函数"""
    while True:
        show_menu()
        
        try:
            choice = input("\n请选择测试选项 (0-5): ").strip()
            
            if choice == "0":
                print("退出测试工具")
                break
            elif choice == "1":
                test_print_api()
            elif choice == "2":
                test_text_print()
            elif choice == "3":
                test_custom_message()
            elif choice == "4":
                list_system_printers()
            elif choice == "5":
                run_full_test()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n\n用户中断，退出测试工具")
            break
        except Exception as e:
            print(f"\n❌ 测试过程中出现错误: {e}")


if __name__ == "__main__":
    main()
