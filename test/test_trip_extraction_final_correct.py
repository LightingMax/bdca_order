#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终正确版行程信息提取功能测试
基于准确的文本结构进行解析
"""

import os
import sys
import re
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def parse_trip_info_final_correct(text):
    """
    最终正确版：基于准确的文本结构进行解析
    
    从实际文本可以看到的结构：
    序号
    服务商
    车型
    上车时间
    城市
    起点
    终点
    金额(元)
    1
    旅程易到
    旅程易到经济型
    2024-06-19 12:32
    北京市
    北京南站-东停车场M
    层(夹层)-B2~B5通道
    航天智能院
    53.89元
    2
    旅程易到
    旅程易到经济型
    2024-06-20 18:59
    北京市
    航天智能院
    汉庭优佳北京石景山首钢园酒店
    16.12元
    3
    旅程易到
    旅程易到经济型
    2024-06-21 08:18
    北京市
    汉庭优佳酒店(北
    京石景山首钢园店)
    北京南站(东进站口)
    74.55元
    """
    trips = []
    
    try:
        lines = text.split('\n')
        
        # 查找数据开始位置（跳过表头）
        data_start = -1
        for i, line in enumerate(lines):
            if line.strip() == '1':  # 第一个序号
                data_start = i
                break
        
        if data_start == -1:
            print("❌ 未找到数据开始位置")
            return []
        
        print(f"✅ 找到数据开始位置: 第{data_start+1}行")
        
        # 解析行程数据
        i = data_start
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # 跳过说明文字
            if '说明：' in line or '页码：' in line:
                break
            
            # 检查是否是序号（新行程开始）
            if line.isdigit():
                trip = {}
                trip['sequence'] = line
                print(f"开始解析行程 {line}")
                
                # 按照实际观察到的结构解析
                # 序号 -> 服务商 -> 车型 -> 上车时间 -> 城市 -> 起点 -> 终点 -> 金额
                
                # 读取服务商
                i += 1
                if i < len(lines):
                    trip['service_provider'] = lines[i].strip()
                    print(f"  服务商: {trip['service_provider']}")
                
                # 读取车型
                i += 1
                if i < len(lines):
                    trip['car_type'] = lines[i].strip()
                    print(f"  车型: {trip['car_type']}")
                
                # 读取上车时间
                i += 1
                if i < len(lines):
                    trip['pickup_time'] = lines[i].strip()
                    print(f"  上车时间: {trip['pickup_time']}")
                
                # 读取城市
                i += 1
                if i < len(lines):
                    trip['city'] = lines[i].strip()
                    print(f"  城市: {trip['city']}")
                
                # 读取起点（可能跨多行）
                i += 1
                if i < len(lines):
                    start_point = lines[i].strip()
                    print(f"  起点第1行: {start_point}")
                    i += 1
                    # 检查下一行是否是起点的延续
                    if i < len(lines) and not lines[i].strip().isdigit() and '元' not in lines[i] and '说明：' not in lines[i]:
                        start_point += lines[i].strip()
                        print(f"  起点第2行: {lines[i].strip()}")
                        i += 1
                    trip['start_point'] = start_point
                    print(f"  完整起点: {trip['start_point']}")
                
                # 读取终点
                if i < len(lines):
                    end_point = lines[i].strip()
                    print(f"  终点: {end_point}")
                    i += 1
                    trip['end_point'] = end_point
                
                # 读取金额
                if i < len(lines):
                    amount_line = lines[i].strip()
                    print(f"  金额行: {amount_line}")
                    amount_match = re.search(r'(\d+\.?\d*)\s*元', amount_line)
                    if amount_match:
                        trip['amount'] = float(amount_match.group(1))
                        print(f"  解析金额: {trip['amount']}")
                    i += 1
                
                trips.append(trip)
                print(f"✅ 完成解析行程: {trip}")
                print("-" * 40)
            else:
                i += 1
        
        return trips
        
    except Exception as e:
        print(f"最终正确版解析失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_trip_extraction():
    """测试行程信息提取功能"""
    print("🧪 测试行程信息提取功能（最终正确版）")
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
        
        # 提取PDF文本
        print(f"\n🔄 开始提取PDF文本...")
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(full_path)
            
            if len(doc) == 0:
                print("❌ PDF文件没有页面")
                doc.close()
                return False
            
            # 提取文本
            full_text = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    full_text += page_text + "\n"
            
            doc.close()
            
            if not full_text.strip():
                print("❌ PDF文件没有可提取的文本内容")
                return False
            
            print(f"✅ 成功提取PDF文本，总长度: {len(full_text)} 字符")
            
        except Exception as e:
            print(f"❌ 文本提取失败: {e}")
            return False
        
        # 测试最终正确版解析
        print(f"\n🔄 测试最终正确版解析...")
        trips = parse_trip_info_final_correct(full_text)
        
        if trips:
            print(f"✅ 最终正确版解析成功，解析到 {len(trips)} 个行程信息:")
            for i, trip in enumerate(trips, 1):
                print(f"  行程{i}: {trip}")
        else:
            print("❌ 最终正确版解析失败")
            return False
        
        # 生成格式化的行程记录
        print(f"\n📋 格式化行程记录:")
        print("=" * 50)
        print("行程记录")
        print("=" * 50)
        for trip in trips:
            # 确保所有必要字段都存在
            sequence = trip.get('sequence', '未知')
            pickup_time = trip.get('pickup_time', '未知时间')
            city = trip.get('city', '未知城市')
            start_point = trip.get('start_point', '未知起点')
            end_point = trip.get('end_point', '未知终点')
            amount = trip.get('amount', 0.0)
            
            record = f"{sequence}, {pickup_time}, {city}, {start_point}, {end_point}, {amount:.2f}元"
            print(record)
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 行程信息提取功能测试（最终正确版）")
    print("=" * 60)
    
    # 检查PyMuPDF
    try:
        import fitz
        print(f"✅ PyMuPDF版本: {fitz.version}")
    except ImportError:
        print("❌ PyMuPDF不可用，请先安装")
        return False
    
    # 运行测试
    success = test_trip_extraction()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试成功！行程信息提取功能正常工作")
        print("\n💡 解析逻辑已修复，可以集成到主系统中")
    else:
        print("⚠️ 测试失败，需要进一步调试")
    
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
