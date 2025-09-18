#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试PyMuPDF的表格提取功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_pymupdf_tables():
    """测试PyMuPDF的表格提取功能"""
    print("🧪 测试PyMuPDF表格提取功能")
    print("=" * 60)
    
    try:
        # 测试文件路径
        test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
        full_path = os.path.join(project_root, test_file)
        
        print(f"📄 测试文件: {test_file}")
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            print(f"❌ 测试文件不存在: {full_path}")
            return False
        
        # 使用PyMuPDF提取表格
        print(f"\n🔄 开始提取PDF表格...")
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(full_path)
            
            if len(doc) == 0:
                print("❌ PDF文件没有页面")
                doc.close()
                return False
            
            # 提取第一页的表格
            page = doc.load_page(0)
            
            # 尝试提取表格
            try:
                # 使用PyMuPDF的表格提取功能
                tables = page.find_tables()
                print(f"✅ 找到 {len(tables)} 个表格")
                
                for i, table in enumerate(tables):
                    print(f"\n📋 表格 {i+1}:")
                    try:
                        # 提取表格数据
                        table_data = table.extract()
                        print(f"表格数据: {table_data}")
                        
                        # 转换为更易读的格式
                        for row_idx, row in enumerate(table_data):
                            print(f"  行{row_idx+1}: {row}")
                            
                    except Exception as e:
                        print(f"提取表格数据失败: {e}")
                        
            except Exception as e:
                print(f"表格提取失败: {e}")
                print("尝试其他方法...")
                
                # 尝试使用文本提取
                text = page.get_text()
                print(f"文本内容: {text}")
                
            doc.close()
            
        except Exception as e:
            print(f"❌ PDF处理失败: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 PyMuPDF表格提取功能测试")
    print("=" * 60)
    
    # 检查PyMuPDF
    try:
        import fitz
        print(f"✅ PyMuPDF版本: {fitz.version}")
    except ImportError:
        print("❌ PyMuPDF不可用，请先安装")
        return False
    
    # 运行测试
    success = test_pymupdf_tables()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试完成！")
    else:
        print("⚠️ 测试失败")
    
    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
