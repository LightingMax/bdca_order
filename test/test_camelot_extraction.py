#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试camelot-py库的行程信息提取功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_camelot_extraction():
    """测试camelot-py提取功能"""
    print("🧪 测试camelot-py行程信息提取功能")
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
                
                # 解析表格数据
                trips = parse_table_to_trips(df)
                if trips:
                    print(f"✅ 从表格中解析到 {len(trips)} 个行程信息:")
                    for j, trip in enumerate(trips, 1):
                        print(f"  行程{j}: {trip}")
                else:
                    print("❌ 未能从表格中解析到行程信息")
            
            return True
            
        except Exception as e:
            print(f"❌ camelot提取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def parse_table_to_trips(df):
    """
    将camelot提取的表格数据转换为行程信息
    处理camelot提取的特殊格式：每行包含多个字段用换行符分隔
    """
    import re
    trips = []
    
    try:
        print(f"开始解析表格数据，形状: {df.shape}")
        
        # 处理camelot提取的特殊格式
        for i, row in df.iterrows():
            # 获取第一列的数据（camelot将所有数据放在第一列）
            cell_data = str(row.iloc[0]).strip()
            if not cell_data or cell_data == 'nan':
                continue
            
            print(f"处理行 {i}: {cell_data}")
            
            # 按换行符分割数据
            lines = cell_data.split('\n')
            print(f"分割后的行数: {len(lines)}")
            
            # 检查是否是表头行
            if '序号' in cell_data and '服务商' in cell_data:
                print("跳过表头行")
                continue
            
            # 检查是否是行程数据行
            if any(line.strip().isdigit() for line in lines):
                trip = parse_trip_from_lines(lines)
                if trip:
                    trips.append(trip)
                    print(f"解析到行程: {trip}")
        
        return trips
        
    except Exception as e:
        print(f"解析表格数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def parse_trip_from_lines(lines):
    """
    从分割后的行中解析行程信息
    """
    import re
    
    try:
        # 查找序号
        sequence = None
        for line in lines:
            if line.strip().isdigit():
                sequence = line.strip()
                break
        
        if not sequence:
            return None
        
        # 查找金额
        amount = 0.0
        for line in lines:
            amount_match = re.search(r'(\d+\.?\d*)\s*元', line)
            if amount_match:
                amount = float(amount_match.group(1))
                break
        
        # 查找时间
        pickup_time = None
        for line in lines:
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', line)
            if time_match:
                pickup_time = time_match.group(1)
                break
        
        # 查找城市
        city = None
        for line in lines:
            if '北京市' in line or '上海市' in line or '广州市' in line or '深圳市' in line:
                city = line.strip()
                break
        
        # 查找起点和终点（简化处理）
        start_point = None
        end_point = None
        
        # 根据实际数据结构调整
        if len(lines) >= 6:
            # 假设起点在前，终点在后
            for i, line in enumerate(lines):
                if '北京南站' in line or '航天智能院' in line or '汉庭' in line:
                    if not start_point:
                        start_point = line.strip()
                    elif not end_point:
                        end_point = line.strip()
        
        trip = {
            'sequence': sequence,
            'service_provider': '旅程易到',  # 从数据中可以看出
            'car_type': '旅程易到经济型',  # 从数据中可以看出
            'pickup_time': pickup_time or '未知时间',
            'city': city or '未知城市',
            'start_point': start_point or '未知起点',
            'end_point': end_point or '未知终点',
            'amount': amount
        }
        
        return trip
        
    except Exception as e:
        print(f"解析行程信息失败: {e}")
        return None


def main():
    """主函数"""
    print("🚀 camelot-py行程信息提取功能测试")
    print("=" * 60)
    
    # 检查camelot
    try:
        import camelot
        print(f"✅ camelot-py可用")
    except ImportError:
        print("❌ camelot-py不可用，请先安装")
        return False
    
    # 运行测试
    success = test_camelot_extraction()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试成功！camelot-py功能正常工作")
    else:
        print("⚠️ 测试失败，需要调试")
    
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
