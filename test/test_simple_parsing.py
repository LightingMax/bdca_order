#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试简化的行程信息解析逻辑
使用camelot-py流式模式 + 正则表达式
"""

import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import camelot
import pdfplumber
import pandas as pd

def parse_trip_info_with_regex(text_lines):
    """
    使用正则表达式解析行程信息
    1. 匹配序号行（纯数字或包含换行符的数字）
    2. 提取数字开头的行直到"说明："行停止
    """
    print(f"🔍 开始正则解析，文本行数: {len(text_lines)}")
    
    trips = []
    current_trip = []
    in_trip = False
    
    for i, line in enumerate(text_lines):
        line = line.strip()
        if not line:
            continue
            
        print(f"第{i+1:2d}行: '{line}'")
        
        # 检查是否到达"说明："行
        if line.startswith("说明："):
            print(f"  → 到达说明行，停止解析")
            break
        
        # 匹配序号行（纯数字或包含换行符的数字，如"1\n旅程易到"）
        if re.match(r'^\d+', line):
            # 如果之前有行程数据，保存它
            if current_trip and in_trip:
                trip_info = parse_single_trip_data(current_trip)
                if trip_info:
                    trips.append(trip_info)
                    print(f"  → 保存行程: {trip_info}")
            
            # 开始新的行程，处理包含换行符的情况
            if '\n' in line:
                # 分割换行符，取第一部分作为序号
                parts = line.split('\n')
                sequence = parts[0].strip()
                current_trip = [sequence]
                # 如果有其他部分，也添加到行程数据中
                for part in parts[1:]:
                    if part.strip():
                        current_trip.append(part.strip())
                print(f"  → 发现序号行(含换行): {line} -> 序号: {sequence}")
            else:
                current_trip = [line]
                print(f"  → 发现序号行: {line}")
            
            in_trip = True
            continue
        
        # 如果在行程中，收集数据
        if in_trip:
            current_trip.append(line)
            print(f"  → 添加到行程数据")
    
    # 处理最后一个行程
    if current_trip and in_trip:
        trip_info = parse_single_trip_data(current_trip)
        if trip_info:
            trips.append(trip_info)
            print(f"  → 保存最后一个行程: {trip_info}")
    
    print(f"✅ 总共解析到 {len(trips)} 个行程")
    return trips


def parse_trip_row_data_with_context(df, row_index, row_data):
    """
    解析DataFrame中一行的行程数据，并尝试从相邻行获取起点信息
    """
    print(f"  📋 解析行数据(带上下文): {row_data}")
    
    # 先解析当前行的数据
    trip = parse_trip_row_data(row_data)
    if not trip:
        return None
    
    # 如果起点是"未知起点"或空字符串，尝试从相邻行获取起点信息
    if trip.get('start_point') == '未知起点' or trip.get('start_point') == '':
        print(f"  🔍 尝试从相邻行获取起点信息...")
        
        # 收集所有可能的起点信息
        start_point_parts = []
        
        # 检查前一行（可能包含起点的第一部分）
        if row_index - 1 >= 0:
            prev_row = list(df.iloc[row_index - 1])
            prev_row_clean = [str(cell).strip() for cell in prev_row if str(cell).strip() and str(cell).strip() != 'nan']
            
            print(f"  📋 前一行数据: {prev_row_clean}")
            
            # 如果前一行有数据且不包含序号，可能是起点信息
            if prev_row_clean and not any(re.match(r'^\d+', str(cell)) for cell in prev_row_clean):
                for cell in prev_row_clean:
                    if cell and not any(keyword in cell for keyword in ['说明：', '页码：', '序号', '服务商', '车型', '上车时间', '城市', '起点', '终点', '金额']):
                        start_point_parts.append(cell)
        
        # 检查下一行（可能包含起点的第二部分）
        if row_index + 1 < len(df):
            next_row = list(df.iloc[row_index + 1])
            next_row_clean = [str(cell).strip() for cell in next_row if str(cell).strip() and str(cell).strip() != 'nan']
            
            print(f"  📋 下一行数据: {next_row_clean}")
            
            # 如果下一行有数据且不包含序号，可能是起点信息
            if next_row_clean and not any(re.match(r'^\d+', str(cell)) for cell in next_row_clean):
                for cell in next_row_clean:
                    if cell and not any(keyword in cell for keyword in ['说明：', '页码：', '序号', '服务商', '车型', '上车时间', '城市', '起点', '终点', '金额']):
                        start_point_parts.append(cell)
        
        # 组合起点信息
        if start_point_parts:
            trip['start_point'] = ' '.join(start_point_parts)
            print(f"  ✅ 组合起点信息: {trip['start_point']}")
        else:
            print(f"  ⚠️ 未能找到起点信息")
    
    return trip


def parse_trip_row_data(row_data):
    """
    解析DataFrame中一行的行程数据
    适配标准表格格式：[序号, 服务商, 车型, 上车时间, 城市, 起点, 终点, 金额]
    """
    print(f"  📋 解析行数据: {row_data}")
    
    # 保留所有列，包括空值，但转换为字符串
    clean_cells = []
    for cell in row_data:
        cell_str = str(cell).strip()
        if cell_str == 'nan':
            clean_cells.append('')  # 将nan转换为空字符串
        else:
            clean_cells.append(cell_str)
    
    print(f"  📋 清理后的单元格: {clean_cells}")
    
    if len(clean_cells) < 8:
        print(f"  ⚠️ 行数据不足，期望8列，实际{len(clean_cells)}列: {clean_cells}")
        return None
    
    # 标准表格格式：[序号, 服务商, 车型, 上车时间, 城市, 起点, 终点, 金额]
    trip = {
        'sequence': clean_cells[0] if len(clean_cells) > 0 else '未知',
        'service_provider': clean_cells[1] if len(clean_cells) > 1 else '未知',
        'car_type': clean_cells[2] if len(clean_cells) > 2 else '未知',
        'pickup_time': clean_cells[3] if len(clean_cells) > 3 else '未知时间',
        'city': clean_cells[4] if len(clean_cells) > 4 else '未知城市',
        'start_point': clean_cells[5] if len(clean_cells) > 5 else '未知起点',
        'end_point': clean_cells[6] if len(clean_cells) > 6 else '未知终点',
        'amount': clean_cells[7] if len(clean_cells) > 7 else '0元',
        'raw_data': clean_cells
    }
    
    print(f"  ✅ 解析结果: {trip}")
    return trip


def parse_single_trip_data(trip_lines):
    """
    解析单个行程的数据（保留兼容性）
    """
    print(f"  📋 解析行程数据: {trip_lines}")
    
    if len(trip_lines) < 3:
        print(f"  ⚠️ 行程数据不足: {trip_lines}")
        return None
    
    # 去掉空行
    clean_lines = [line.strip() for line in trip_lines if line.strip()]
    
    if len(clean_lines) < 3:
        print(f"  ⚠️ 清理后行程数据不足: {clean_lines}")
        return None
    
    # 基本结构：序号, 服务商, 车型, 时间, 城市, 起点, 终点, 金额
    trip = {
        'sequence': clean_lines[0] if len(clean_lines) > 0 else '未知',
        'service_provider': clean_lines[1] if len(clean_lines) > 1 else '未知',
        'car_type': clean_lines[2] if len(clean_lines) > 2 else '未知',
        'pickup_time': clean_lines[3] if len(clean_lines) > 3 else '未知时间',
        'city': clean_lines[4] if len(clean_lines) > 4 else '未知城市',
        'start_point': clean_lines[5] if len(clean_lines) > 5 else '未知起点',
        'end_point': clean_lines[6] if len(clean_lines) > 6 else '未知终点',
        'amount': clean_lines[7] if len(clean_lines) > 7 else '0元',
        'raw_data': clean_lines
    }
    
    print(f"  ✅ 解析结果: {trip}")
    return trip


def test_pdfplumber_parsing():
    """测试pdfplumber解析 - 尝试不同策略"""
    # 测试文件路径
    test_file = "temp_files/【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print(f"🧪 测试pdfplumber解析")
    print(f"📁 测试文件: {test_file}")
    print("=" * 60)
    
    # 尝试不同的策略组合
    strategies = [
        {"name": "默认策略", "table_settings": {}},
        {"name": "lines策略", "table_settings": {"vertical_strategy": "lines", "horizontal_strategy": "lines"}},
        {"name": "text策略", "table_settings": {"vertical_strategy": "text", "horizontal_strategy": "text"}},
        {"name": "混合策略1", "table_settings": {"vertical_strategy": "lines", "horizontal_strategy": "text"}},
        {"name": "混合策略2", "table_settings": {"vertical_strategy": "text", "horizontal_strategy": "lines"}},
    ]
    
    try:
        with pdfplumber.open(test_file) as pdf:
            page = pdf.pages[0]  # 获取第一页
            
            for strategy in strategies:
                print(f"\n🔍 尝试策略: {strategy['name']}")
                print(f"📊 参数: {strategy['table_settings']}")
                
                # 使用指定策略提取表格
                tables = page.extract_tables(table_settings=strategy['table_settings'])
                
                if not tables:
                    print("❌ 未找到表格数据")
                    continue
                
                print(f"✅ 找到 {len(tables)} 个表格")
                
                # 获取第一个表格的数据
                table_data = tables[0]
                print(f"📋 表格数据:")
                for i, row in enumerate(table_data):
                    print(f"第{i}行: {row}")
                print("-" * 40)
                
                # 检查表格质量
                if len(table_data) > 1 and len(table_data[0]) >= 8:
                    print(f"✅ 表格结构良好，列数: {len(table_data[0])}")
                    
                    # 尝试解析行程数据
                    trips = []
                    for row_idx, row in enumerate(table_data):
                        if row_idx == 0:  # 跳过表头
                            continue
                            
                        print(f"📋 处理行 {row_idx}: {row}")
                        
                        # 检查是否是行程行（序号列有数字）
                        if len(row) > 0 and row[0] and str(row[0]).strip().isdigit():
                            sequence = str(row[0]).strip()
                            print(f"  → 发现行程行: 序号={sequence}")
                            
                            # 解析行程数据
                            trip = {
                                'sequence': sequence,
                                'service_provider': str(row[1]).strip() if len(row) > 1 and row[1] else '未知',
                                'car_type': str(row[2]).strip() if len(row) > 2 and row[2] else '未知',
                                'pickup_time': str(row[3]).strip() if len(row) > 3 and row[3] else '未知时间',
                                'city': str(row[4]).strip() if len(row) > 4 and row[4] else '未知城市',
                                'start_point': str(row[5]).strip() if len(row) > 5 and row[5] else '未知起点',
                                'end_point': str(row[6]).strip() if len(row) > 6 and row[6] else '未知终点',
                                'amount': str(row[7]).strip() if len(row) > 7 and row[7] else '0元',
                                'raw_data': row
                            }
                            
                            trips.append(trip)
                            print(f"  → 解析成功: {trip}")
                    
                    print(f"📋 总共解析到 {len(trips)} 个行程")
                    
                    if len(trips) > 0:
                        print(f"🎉 策略 {strategy['name']} 成功解析到行程数据！")
                        return trips
                else:
                    print(f"⚠️ 表格结构不理想，列数: {len(table_data[0]) if table_data else 0}")
            
            print("❌ 所有策略都未能成功解析")
            return []
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_camelot_stream_parsing():
    """测试camelot流式模式 + 正则解析"""
    # 测试文件路径
    test_file = "temp_files/【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return
    
    print(f"🧪 测试camelot流式模式 + 正则解析")
    print(f"📁 测试文件: {test_file}")
    print("=" * 60)
    
    try:
        # 使用camelot-py流式模式提取表格
        print("📊 使用camelot-py流式模式提取表格...")
        tables = camelot.read_pdf(test_file, pages='1', flavor='stream')
        
        if not tables:
            print("❌ 未找到表格数据")
            return
        
        print(f"✅ 找到 {len(tables)} 个表格")
        
        # 获取第一个表格的数据
        df = tables[0].df
        print(f"📋 表格形状: {df.shape}")
        print(f"📋 表格数据:")
        print(df)
        print("-" * 40)
        
        # 直接从DataFrame的行中提取行程数据
        # 从camelot输出看，行程数据在第6、8、10行
        trips = []
        
        print(f"📋 分析DataFrame行数据:")
        for index, row in df.iterrows():
            print(f"第{index}行: {list(row)}")
        
        # 找到包含行程数据的行（包含序号和服务商的行）
        for index, row in df.iterrows():
            row_data = list(row)
            # 检查这一行是否包含行程数据（序号列有数字，服务商列有内容）
            if len(row_data) >= 2:
                sequence_cell = str(row_data[0]).strip()
                service_cell = str(row_data[1]).strip()
                
                # 检查是否是行程行：序号列是纯数字，服务商列有内容
                if re.match(r'^\d+$', sequence_cell) and service_cell and service_cell != 'nan':
                    print(f"  → 发现行程行 {index}: 序号={sequence_cell}, 服务商={service_cell}")
                    
                    # 解析这一行的所有数据，并尝试从相邻行获取起点信息
                    trip_data = parse_trip_row_data_with_context(df, index, row_data)
                    if trip_data:
                        trips.append(trip_data)
                        print(f"  → 解析成功: {trip_data}")
                    # 不要break，继续查找其他行程行
        
        print(f"📋 总共解析到 {len(trips)} 个行程")
        return trips
        
        print(f"📝 提取的文本行: {text_lines}")
        print("-" * 40)
        
        # 使用正则表达式解析行程信息
        trips = parse_trip_info_with_regex(text_lines)
        
        print(f"\n🎯 最终结果:")
        print(f"✅ 解析成功，提取到 {len(trips)} 个行程")
        print()
        
        for i, trip in enumerate(trips, 1):
            print(f"行程 {i}:")
            print(f"  序号: {trip.get('sequence', '未知')}")
            print(f"  服务商: {trip.get('service_provider', '未知')}")
            print(f"  车型: {trip.get('car_type', '未知')}")
            print(f"  时间: {trip.get('pickup_time', '未知时间')}")
            print(f"  城市: {trip.get('city', '未知城市')}")
            print(f"  起点: {trip.get('start_point', '未知起点')}")
            print(f"  终点: {trip.get('end_point', '未知终点')}")
            print(f"  金额: {trip.get('amount', '0元')}")
            print(f"  原始数据: {trip.get('raw_data', [])}")
            print()
        
        # 验证是否提取到3个行程
        if len(trips) == 3:
            print("✅ 成功提取到3个行程，符合预期")
        else:
            print(f"⚠️ 期望3个行程，实际提取到{len(trips)}个")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔬 开始测试PDF解析方法对比")
    print("=" * 80)
    
    print("\n1️⃣ 测试pdfplumber解析:")
    test_pdfplumber_parsing()
    
    print("\n" + "=" * 80)
    print("\n2️⃣ 测试camelot-py解析:")
    test_camelot_stream_parsing()
