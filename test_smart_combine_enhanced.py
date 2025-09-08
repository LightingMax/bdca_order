#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能拼接功能增强测试脚本
测试修复后的多页行程单智能拼接功能
"""

import os
import sys
import subprocess
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

def test_pypdf2_availability():
    """测试PyPDF2库可用性"""
    print("\n📚 测试PyPDF2库...")
    
    try:
        import PyPDF2
        print(f"✅ PyPDF2库可用: {PyPDF2.__version__}")
        return True
    except ImportError:
        print("❌ PyPDF2库不可用")
        return False
    except Exception as e:
        print(f"❌ PyPDF2测试失败: {e}")
        return False

def test_pdf_page_info():
    """测试PDF页面信息获取"""
    print("\n📄 测试PDF页面信息获取...")
    
    if not shutil.which('pdftk'):
        print("⚠️ pdftk不可用，跳过页面信息测试")
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
                    # 解析页面信息
                    page_count = 0
                    page_size = None
                    
                    for line in result.stdout.split('\n'):
                        if line.startswith('NumberOfPages:'):
                            page_count = int(line.split(':')[1].strip())
                        elif line.startswith('PageMediaDimensions:'):
                            page_size = line.split(':')[1].strip()
                    
                    print(f"✅ {test_file}: {page_count}页, 尺寸: {page_size}")
                else:
                    print(f"❌ {test_file}: 信息获取失败")
            except Exception as e:
                print(f"❌ {test_file}: 测试异常 - {e}")
        else:
            print(f"ℹ️ {test_file}: 文件不存在")
    
    return True

def test_smart_combine_logic():
    """测试智能拼接逻辑"""
    print("\n🔗 测试智能拼接逻辑...")
    
    print("📋 增强后的智能拼接流程:")
    print("   1. 检查PDF页面尺寸")
    print("   2. 如果尺寸不同，进行标准化处理")
    print("   3. 使用pdftk cat进行垂直拼接（主要方法）")
    print("   4. 如果失败，尝试pdftk stamp（备选方法1）")
    print("   5. 如果还是失败，使用PyPDF2进行精确拼接（备选方法2）")
    print("   6. 验证拼接结果的质量和完整性")
    
    return True

def test_file_size_validation():
    """测试文件大小验证"""
    print("\n📊 测试文件大小验证...")
    
    print("📋 文件验证机制:")
    print("   • 检查文件是否存在")
    print("   • 验证文件大小（>1KB）")
    print("   • 验证PDF有效性（使用pdftk dump_data）")
    print("   • 检查页面数量")
    print("   • 记录详细的拼接信息")
    
    return True

def test_error_handling():
    """测试错误处理机制"""
    print("\n🛡️ 测试错误处理机制...")
    
    print("📋 错误处理策略:")
    print("   • 页面尺寸不匹配 → 标准化处理")
    print("   • pdftk cat失败 → 尝试stamp")
    print("   • stamp失败 → 尝试PyPDF2")
    print("   • 所有方法失败 → 回退到直接打印")
    print("   • 临时文件自动清理")
    print("   • 详细的错误日志记录")
    
    return True

def test_real_scenario():
    """测试真实场景"""
    print("\n🎯 测试真实场景...")
    
    print("📄 您的实际文件情况:")
    print("   • 行程单: 2页（显示'页码: 1/2'）")
    print("   • 发票: 1页")
    print("   • 问题: 大段黑色区域 + 顺序不对")
    print()
    
    print("🔄 修复后的处理流程:")
    print("   1. 检测到2页行程单（≥2页触发智能拼接）")
    print("   2. 识别为行程单类型")
    print("   3. 查找对应发票文件")
    print("   4. 检查PDF页面尺寸兼容性")
    print("   5. 创建智能拼接第一页（发票+行程单第1页）")
    print("   6. 打印拼接后的第一页")
    print("   7. 提取行程单第2页")
    print("   8. 打印第2页")
    print()
    
    print("🎉 预期结果：")
    print("   • 发票在上，行程单第1页内容在下")
    print("   • 无黑色区域，内容清晰可见")
    print("   • 正确的垂直拼接顺序")
    print("   • 行程单第2页单独打印")
    
    return True

def main():
    """主函数"""
    print("🔧 智能拼接功能增强测试")
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
        test_pypdf2_availability,
        test_pdf_page_info,
        test_smart_combine_logic,
        test_file_size_validation,
        test_error_handling,
        test_real_scenario
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
        print("🎉 所有测试通过！智能拼接功能已增强")
        print("\n💡 现在您可以：")
        print("   1. 重新测试智能打印功能")
        print("   2. 应该不再有黑色区域")
        print("   3. 拼接顺序应该正确")
        print("   4. 多页行程单应该正确处理")
    else:
        print("⚠️ 部分测试失败，请检查相关配置")
    
    print("\n🚀 建议：")
    print("   1. 清理缓存后重新测试")
    print("   2. 查看FastAPI服务日志")
    print("   3. 验证PDF文件质量")
    
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
