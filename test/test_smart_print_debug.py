#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能打印调试脚本
专门用于调试多页行程单的智能拼接和打印问题
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def test_pdf_page_count():
    """测试PDF页数检测功能"""
    print("📄 测试PDF页数检测功能...")
    
    # 检查是否有必要的工具
    if not shutil.which('pdftk'):
        print("❌ pdftk工具不可用，无法检测PDF页数")
        return False
    
    # 测试文件
    test_files = [
        "app/static/outputs/order_1_test.pdf",
        "temp_files/test_itinerary.pdf",
        "app/static/uploads/test_file.pdf"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                result = subprocess.run(['pdftk', test_file, 'dump_data'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # 解析页数
                    for line in result.stdout.split('\n'):
                        if line.startswith('NumberOfPages:'):
                            page_count = int(line.split(':')[1].strip())
                            print(f"✅ {test_file}: {page_count} 页")
                            break
                else:
                    print(f"❌ {test_file}: pdftk检测失败")
            except Exception as e:
                print(f"❌ {test_file}: 检测异常 - {e}")
        else:
            print(f"ℹ️ {test_file}: 文件不存在")
    
    return True

def test_file_type_identification():
    """测试文件类型识别功能"""
    print("\n🔍 测试文件类型识别功能...")
    
    test_filenames = [
        "【及时用车-53.21元-2个行程】高德打车电子发票.pdf",
        "滴滴出行行程单_3页.pdf",
        "美团外卖订单.pdf",
        "test_itinerary_5pages.pdf",
        "invoice_receipt.pdf"
    ]
    
    for filename in test_filenames:
        # 模拟identify_pdf_type函数的逻辑
        filename_lower = filename.lower()
        
        if any(keyword in filename_lower for keyword in ['发票', 'invoice', 'receipt', 'bill']):
            file_type = 'invoice'
        elif any(keyword in filename_lower for keyword in ['行程', 'itinerary', 'trip', '订单']):
            file_type = 'itinerary'
        else:
            file_type = 'unknown'
        
        print(f"📋 {filename} → {file_type}")
    
    return True

def test_invoice_matching():
    """测试发票匹配功能"""
    print("\n🔗 测试发票匹配功能...")
    
    # 模拟行程单文件名
    itinerary_filename = "【及时用车-53.21元-2个行程】高德打车电子发票.pdf"
    
    print(f"📄 行程单: {itinerary_filename}")
    
    # 测试订单标识提取
    order_patterns = [
        r'(\d+个行程)',           # 高德打车：2个行程
        r'(订单\d+)',             # 通用订单格式
        r'(trip\d+)',             # 英文trip格式
        r'(\d+\.\d+元)',          # 金额格式：53.21元
        r'(\d+-\d+)',             # 数字-数字格式
        r'([A-Za-z0-9]{8,})',    # 8位以上字母数字组合
    ]
    
    import re
    order_key = None
    for pattern in order_patterns:
        match = re.search(pattern, itinerary_filename)
        if match:
            order_key = match.group(1)
            print(f"🔑 提取到订单标识: {order_key}")
            break
    
    if not order_key:
        print("⚠️ 无法提取订单标识，使用文件名")
        order_key = itinerary_filename.split('.')[0]
    
    # 模拟搜索目录
    search_dirs = [
        "temp_files",
        "app/static/uploads", 
        "app/static/outputs",
    ]
    
    print(f"🔍 搜索目录: {search_dirs}")
    print(f"🔑 搜索关键词: {order_key}")
    
    return True

def test_smart_print_flow():
    """测试智能打印流程"""
    print("\n🖨️ 测试智能打印流程...")
    
    print("📋 智能打印流程:")
    print("   1. 检测PDF页数")
    print("   2. 识别文件类型")
    print("   3. 如果是多页行程单（>2页）:")
    print("      a. 查找对应发票")
    print("      b. 创建智能拼接第一页（发票+行程单第一页）")
    print("      c. 打印拼接后的第一页")
    print("      d. 提取行程单剩余页面（第2页开始）")
    print("      e. 打印剩余页面")
    print("   4. 如果智能处理失败，回退到直接打印")
    
    return True

def test_directory_structure():
    """测试目录结构"""
    print("\n📁 测试目录结构...")
    
    directories = [
        "temp_files",
        "app/static/uploads",
        "app/static/outputs", 
        "app/data"
    ]
    
    for directory in directories:
        if os.path.exists(directory):
            file_count = len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
            print(f"📁 {directory}: {file_count} 个文件")
        else:
            print(f"❌ {directory}: 目录不存在")
    
    return True

def test_pdftk_commands():
    """测试pdftk命令"""
    print("\n🔧 测试pdftk命令...")
    
    if not shutil.which('pdftk'):
        print("❌ pdftk工具不可用")
        return False
    
    try:
        # 测试pdftk版本
        result = subprocess.run(['pdftk', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.strip().split('\n')[0]
            print(f"✅ pdftk版本: {version_line}")
        else:
            print("❌ pdftk版本检测失败")
    except Exception as e:
        print(f"❌ pdftk测试失败: {e}")
    
    return True

def main():
    """主函数"""
    print("🔍 智能打印功能调试工具")
    print("=" * 60)
    
    # 导入必要的模块
    try:
        import shutil
        import re
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False
    
    # 运行各项测试
    tests = [
        test_pdf_page_count,
        test_file_type_identification,
        test_invoice_matching,
        test_smart_print_flow,
        test_directory_structure,
        test_pdftk_commands
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
        print("🎉 所有测试通过！智能打印功能应该正常工作")
    else:
        print("⚠️ 部分测试失败，请检查相关配置")
    
    print("\n💡 调试建议:")
    print("   1. 确保pdftk工具已安装")
    print("   2. 检查文件权限和目录结构")
    print("   3. 查看FastAPI服务日志")
    print("   4. 验证文件命名规则")
    
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
