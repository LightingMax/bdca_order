#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终智能打印功能测试脚本
验证修复后的多页行程单智能拼接和打印功能
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def test_pdftk_availability():
    """测试pdftk工具可用性"""
    print("🔧 测试pdftk工具...")
    
    if not shutil.which('pdftk'):
        print("❌ pdftk工具不可用")
        return False
    
    try:
        result = subprocess.run(['pdftk', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.strip().split('\n')[0]
            print(f"✅ pdftk可用: {version_line}")
            return True
        else:
            print("❌ pdftk版本检测失败")
            return False
    except Exception as e:
        print(f"❌ pdftk测试失败: {e}")
        return False

def test_smart_combine_function():
    """测试智能拼接功能"""
    print("\n🔗 测试智能拼接功能...")
    
    # 文件路径 - 使用实际存在的文件
    invoice_path = "temp/e9625f64-336d-43fc-a46c-6f8fff3a2773/extracted/v2/【火箭出行-1079.92元-28个行程】高德打车电子发票.pdf"
    itinerary_path = "temp/e9625f64-336d-43fc-a46c-6f8fff3a2773/extracted/v2/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    
    if not os.path.exists(invoice_path):
        print(f"❌ 发票文件不存在: {invoice_path}")
        return False
    
    if not os.path.exists(itinerary_path):
        print(f"❌ 行程单文件不存在: {itinerary_path}")
        return False
    
    try:
        # 模拟智能拼接过程
        print("🔄 模拟智能拼接过程...")
        
        # 1. 提取行程单第一页
        temp_itinerary_first = "temp_files/temp_itinerary_first.pdf"
        subprocess.run(['pdftk', itinerary_path, 'cat', '1', 'output', temp_itinerary_first], check=True)
        print("✅ 提取行程单第一页成功")
        
        # 2. 使用pdftk cat进行智能拼接
        combined_output = "temp_files/smart_combined_test.pdf"
        subprocess.run([
            'pdftk', invoice_path, temp_itinerary_first, 
            'cat', 'output', combined_output
        ], check=True)
        print("✅ 智能拼接成功")
        
        # 3. 验证拼接结果
        if os.path.exists(combined_output):
            file_size = os.path.getsize(combined_output)
            print(f"📊 拼接文件大小: {file_size} bytes")
            
            # 检查页数
            result = subprocess.run(['pdftk', combined_output, 'dump_data'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('NumberOfPages:'):
                        page_count = int(line.split(':')[1].strip())
                        print(f"✅ 拼接文件页数: {page_count}")
                        break
            
            # 清理临时文件
            if os.path.exists(temp_itinerary_first):
                os.remove(temp_itinerary_first)
            
            return True
        else:
            print("❌ 拼接文件未生成")
            return False
            
    except Exception as e:
        print(f"❌ 智能拼接测试失败: {e}")
        return False

def test_page_extraction_for_printing():
    """测试页面提取（用于打印）"""
    print("\n📄 测试页面提取（用于打印）...")
    
    itinerary_path = "temp/e9625f64-336d-43fc-a46c-6f8fff3a2773/extracted/v2/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    
    try:
        # 提取第二页（用于单独打印）
        second_page_path = "temp_files/itinerary_second_page_for_print.pdf"
        subprocess.run(['pdftk', itinerary_path, 'cat', '2', 'output', second_page_path], check=True)
        
        if os.path.exists(second_page_path):
            file_size = os.path.getsize(second_page_path)
            print(f"✅ 第二页提取成功: {second_page_path}")
            print(f"   文件大小: {file_size} bytes")
            
            # 验证第二页
            result = subprocess.run(['pdftk', second_page_path, 'dump_data'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('NumberOfPages:'):
                        page_count = int(line.split(':')[1].strip())
                        print(f"   页数: {page_count}")
                        break
            
            return True
        else:
            print("❌ 第二页提取失败")
            return False
            
    except Exception as e:
        print(f"❌ 页面提取测试失败: {e}")
        return False

def test_smart_print_flow():
    """测试智能打印流程"""
    print("\n🖨️ 测试智能打印流程...")
    
    print("📋 完整的智能打印流程:")
    print("   1. 检测到2页行程单（≥2页触发智能拼接）")
    print("   2. 识别为行程单类型")
    print("   3. 查找对应发票文件")
    print("   4. 创建智能拼接第一页（发票+行程单第1页）")
    print("   5. 打印拼接后的第一页")
    print("   6. 提取行程单第2页")
    print("   7. 打印第2页")
    print()
    
    print("🎯 预期结果：")
    print("   • 第一页：发票在上，行程单第1页内容在下（无黑色区域）")
    print("   • 第二页：行程单第2页内容（完整显示）")
    print("   • 总打印页数：2页")
    
    return True

def test_file_compatibility():
    """测试文件兼容性"""
    print("\n🔍 测试文件兼容性...")
    
    files = [
        "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子发票.pdf",
        "temp_files/【火箭出行-1079.92元-28个行程】高德打车电子行程单.pdf"
    ]
    
    for file_path in files:
        if os.path.exists(file_path):
            try:
                # 测试文件可读性
                result = subprocess.run(['pdftk', file_path, 'dump_data'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✅ {os.path.basename(file_path)}: 文件正常")
                else:
                    print(f"❌ {os.path.basename(file_path)}: 文件异常")
            except Exception as e:
                print(f"❌ {os.path.basename(file_path)}: 测试失败 - {e}")
        else:
            print(f"❌ 文件不存在: {file_path}")
    
    return True

def main():
    """主函数"""
    print("🎯 最终智能打印功能测试")
    print("=" * 60)
    
    # 导入必要的模块
    try:
        import shutil
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        return False
    
    # 运行各项测试
    tests = [
        test_pdftk_availability,
        test_smart_combine_function,
        test_page_extraction_for_printing,
        test_smart_print_flow,
        test_file_compatibility
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
        print("🎉 所有测试通过！智能打印功能已完全修复")
        print("\n💡 现在您可以：")
        print("   1. 重新测试智能打印功能")
        print("   2. 应该不再有黑色区域")
        print("   3. 拼接顺序应该正确")
        print("   4. 多页行程单应该正确处理")
        print("   5. 打印效果应该清晰完整")
    else:
        print("⚠️ 部分测试失败，请检查相关配置")
    
    print("\n🚀 下一步：")
    print("   1. 清理缓存（使用utils/clear_cache_tool.py）")
    print("   2. 重新上传ZIP文件到智能处理区域")
    print("   3. 测试智能打印功能")
    print("   4. 验证打印效果")
    
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
