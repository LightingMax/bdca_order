#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试camelot-py提取的表格数据，查看为什么第3个行程没有被提取
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def debug_camelot_extraction():
    """调试camelot提取的表格数据"""
    print("🔍 调试camelot-py表格提取数据")
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
        
        # 使用camelot提取表格
        print(f"\n🔄 开始使用camelot-py提取PDF表格...")
        try:
            import camelot
            
            # 提取表格
            tables = camelot.read_pdf(full_path, pages='1')
            
            if not tables:
                print("❌ 未找到表格数据")
                return False
            
            print(f"✅ 找到 {len(tables)} 个表格")
            
            # 处理每个表格
            for i, table in enumerate(tables):
                print(f"\n📋 处理表格 {i+1}:")
                
                # 获取表格数据
                df = table.df
                print(f"表格形状: {df.shape}")
                print(f"表格数据:")
                print(df)
                
                # 详细分析每一行
                print(f"\n🔍 详细分析每一行:")
                for row_idx, row in df.iterrows():
                    cell_data = str(row.iloc[0]).strip()
                    print(f"\n行 {row_idx}:")
                    print(f"  原始数据: {cell_data}")
                    
                    if cell_data and cell_data != 'nan':
                        lines = cell_data.split('\n')
                        print(f"  分割后行数: {len(lines)}")
                        for line_idx, line in enumerate(lines):
                            print(f"    {line_idx}: '{line}'")
                        
                        # 检查是否包含序号
                        has_digit = any(line.strip().isdigit() for line in lines)
                        print(f"  包含数字序号: {has_digit}")
                        
                        # 检查是否包含金额
                        import re
                        has_amount = any(re.search(r'(\d+\.?\d*)\s*元', line) for line in lines)
                        print(f"  包含金额: {has_amount}")
                        
                        # 检查是否是表头
                        is_header = '序号' in cell_data and '服务商' in cell_data
                        print(f"  是表头行: {is_header}")
            
            return True
            
        except Exception as e:
            print(f"❌ camelot提取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ 调试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 camelot-py表格提取数据调试")
    print("=" * 60)
    
    # 检查camelot
    try:
        import camelot
        print(f"✅ camelot-py可用")
    except ImportError:
        print("❌ camelot-py不可用，请先安装")
        return False
    
    # 运行调试
    success = debug_camelot_extraction()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 调试完成！")
    else:
        print("⚠️ 调试失败")
    
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
