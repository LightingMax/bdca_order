#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试camelot-py的不同参数设置，尝试提取完整的表格数据
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_camelot_different_params():
    """测试camelot的不同参数设置"""
    print("🧪 测试camelot-py不同参数设置")
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
        
        import camelot
        
        # 测试不同的参数组合
        test_configs = [
            {"pages": "1", "flavor": "lattice"},
            {"pages": "1", "flavor": "stream"},
            {"pages": "1", "flavor": "lattice", "line_scale": 40},
            {"pages": "1", "flavor": "stream", "line_scale": 40},
            {"pages": "1", "flavor": "lattice", "copy_text": ["v"]},
            {"pages": "1", "flavor": "stream", "copy_text": ["v"]},
        ]
        
        for i, config in enumerate(test_configs):
            print(f"\n🔄 测试配置 {i+1}: {config}")
            try:
                tables = camelot.read_pdf(full_path, **config)
                
                if tables:
                    print(f"✅ 找到 {len(tables)} 个表格")
                    
                    for j, table in enumerate(tables):
                        df = table.df
                        print(f"  表格 {j+1} 形状: {df.shape}")
                        
                        # 检查是否包含3个行程
                        trip_count = 0
                        for row_idx, row in df.iterrows():
                            cell_data = str(row.iloc[0]).strip()
                            if cell_data and cell_data != 'nan':
                                lines = cell_data.split('\n')
                                # 检查是否包含数字序号
                                if any(line.strip().isdigit() for line in lines):
                                    trip_count += 1
                        
                        print(f"  检测到行程数: {trip_count}")
                        
                        if trip_count >= 3:
                            print(f"  🎉 找到3个或更多行程！")
                            print(f"  表格数据:")
                            print(df)
                            return True
                else:
                    print("❌ 未找到表格")
                    
            except Exception as e:
                print(f"❌ 配置 {i+1} 失败: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_camelot_with_area():
    """测试camelot指定区域提取"""
    print("\n🧪 测试camelot指定区域提取")
    print("=" * 60)
    
    try:
        # 测试文件路径
        test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
        full_path = os.path.join(project_root, test_file)
        
        import camelot
        
        # 尝试不同的区域设置
        area_configs = [
            {"pages": "1", "flavor": "stream", "table_areas": ["0,800,600,0"]},  # 全页面
            {"pages": "1", "flavor": "stream", "table_areas": ["0,600,600,200"]},  # 中间区域
            {"pages": "1", "flavor": "lattice", "table_areas": ["0,800,600,0"]},  # 全页面
        ]
        
        for i, config in enumerate(area_configs):
            print(f"\n🔄 测试区域配置 {i+1}: {config}")
            try:
                tables = camelot.read_pdf(full_path, **config)
                
                if tables:
                    print(f"✅ 找到 {len(tables)} 个表格")
                    
                    for j, table in enumerate(tables):
                        df = table.df
                        print(f"  表格 {j+1} 形状: {df.shape}")
                        print(f"  表格数据:")
                        print(df)
                        
                        # 检查是否包含3个行程
                        trip_count = 0
                        for row_idx, row in df.iterrows():
                            cell_data = str(row.iloc[0]).strip()
                            if cell_data and cell_data != 'nan':
                                lines = cell_data.split('\n')
                                # 检查是否包含数字序号
                                if any(line.strip().isdigit() for line in lines):
                                    trip_count += 1
                        
                        print(f"  检测到行程数: {trip_count}")
                        
                        if trip_count >= 3:
                            print(f"  🎉 找到3个或更多行程！")
                            return True
                else:
                    print("❌ 未找到表格")
                    
            except Exception as e:
                print(f"❌ 区域配置 {i+1} 失败: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 区域测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 camelot-py不同参数设置测试")
    print("=" * 60)
    
    # 检查camelot
    try:
        import camelot
        print(f"✅ camelot-py可用")
    except ImportError:
        print("❌ camelot-py不可用，请先安装")
        return False
    
    # 运行测试
    success1 = test_camelot_different_params()
    success2 = test_camelot_with_area()
    
    print("\n" + "=" * 60)
    if success1 or success2:
        print("🎉 找到能提取3个行程的配置！")
    else:
        print("⚠️ 所有配置都无法提取到3个行程")
        print("💡 可能需要使用其他方法或调整PDF文件")
    
    return success1 or success2


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
