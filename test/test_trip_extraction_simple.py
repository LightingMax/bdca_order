#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试行程信息提取功能（不依赖Flask上下文）
"""

import os
import sys
import re
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def parse_trip_info_from_text(text):
    """
    从文本中解析行程信息（独立版本，不依赖Flask）
    """
    trips = []
    
    try:
        # 按行分割文本
        lines = text.split('\n')
        
        # 查找行程信息的模式
        # 基于实际PDF内容调整模式
        trip_patterns = [
            # 模式1: 序号 服务商 车型 上车时间 城市 起点 终点 金额
            r'(\d+)\s+([^\s]+)\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+(\d+\.?\d*)\s*元',
            # 模式2: 更宽松的匹配，处理多行起点终点
            r'(\d+)\s+([^\s]+)\s+([^\s]+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+([^\s]+)\s+([^\n]+?)\s+(\d+\.?\d*)\s*元',
        ]
        
        # 先尝试逐行匹配
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 尝试匹配各种模式
            for pattern in trip_patterns:
                match = re.search(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 8:
                        trip = {
                            'sequence': groups[0],  # 序号
                            'service_provider': groups[1],  # 服务商
                            'car_type': groups[2],  # 车型
                            'pickup_time': groups[3],  # 上车时间
                            'city': groups[4],  # 城市
                            'start_point': groups[5].strip(),  # 起点
                            'end_point': groups[6].strip(),  # 终点
                            'amount': float(groups[7])  # 金额
                        }
                        trips.append(trip)
                        print(f"解析到行程: {trip}")
                        break
        
        # 如果没有匹配到标准格式，尝试更简单的解析
        if not trips:
            trips = parse_simple_trip_info(lines)
        
        return trips
        
    except Exception as e:
        print(f"解析行程信息失败: {e}")
        return []


def parse_simple_trip_info(lines):
    """
    简单的行程信息解析（备用方案）
    """
    trips = []
    
    try:
        # 查找包含数字和金额的行
        amount_pattern = r'(\d+\.?\d*)\s*元'
        time_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 查找金额
            amount_match = re.search(amount_pattern, line)
            if amount_match:
                amount = float(amount_match.group(1))
                
                # 查找时间
                time_match = re.search(time_pattern, line)
                pickup_time = time_match.group(1) if time_match else "未知时间"
                
                # 尝试提取其他信息
                parts = line.split()
                if len(parts) >= 3:
                    trip = {
                        'sequence': str(len(trips) + 1),  # 序号
                        'pickup_time': pickup_time,  # 上车时间
                        'city': parts[0] if len(parts) > 0 else "未知城市",  # 城市
                        'start_point': parts[1] if len(parts) > 1 else "未知起点",  # 起点
                        'end_point': parts[2] if len(parts) > 2 else "未知终点",  # 终点
                        'amount': amount  # 金额
                    }
                    trips.append(trip)
                    print(f"简单解析到行程: {trip}")
        
        return trips
        
    except Exception as e:
        print(f"简单解析行程信息失败: {e}")
        return []


def extract_trip_info_from_itinerary(pdf_path):
    """
    从行程单PDF中提取行程信息（独立版本）
    """
    print(f"开始从行程单提取行程信息: {pdf_path}")
    
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            print(f"PDF文件没有页面: {pdf_path}")
            doc.close()
            return []
        
        # 提取所有页面的文本
        full_text = ""
        for page_num in range(len(doc)):
            try:
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    full_text += page_text + "\n"
            except Exception as e:
                print(f"提取第{page_num+1}页文本失败: {e}")
                continue
        
        doc.close()
        
        if not full_text.strip():
            print(f"PDF文件没有可提取的文本内容: {pdf_path}")
            return []
        
        print(f"成功提取PDF文本，长度: {len(full_text)} 字符")
        
        # 解析行程信息
        trips = parse_trip_info_from_text(full_text)
        print(f"从行程单中提取到 {len(trips)} 个行程信息")
        
        return trips
        
    except Exception as e:
        print(f"从行程单提取信息失败: {e}")
        return []


def test_trip_extraction():
    """测试行程信息提取功能"""
    print("🧪 测试行程信息提取功能")
    print("=" * 60)
    
    try:
        # 测试文件路径
        test_file = "temp_files/【高德打车-144.56元-3个行程】高德打车电子行程单.pdf"
        full_path = os.path.join(project_root, test_file)
        
        print(f"📄 测试文件: {test_file}")
        print(f"📄 完整路径: {full_path}")
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            print(f"❌ 测试文件不存在: {full_path}")
            return False
        
        file_size = os.path.getsize(full_path)
        print(f"📊 文件大小: {file_size} bytes")
        
        # 测试文本提取
        print(f"\n🔄 开始提取PDF文本...")
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(full_path)
            
            if len(doc) == 0:
                print("❌ PDF文件没有页面")
                doc.close()
                return False
            
            print(f"📄 PDF页数: {len(doc)}")
            
            # 提取所有页面的文本
            full_text = ""
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    if page_text:
                        full_text += page_text + "\n"
                        print(f"📄 第{page_num+1}页文本长度: {len(page_text)} 字符")
                except Exception as e:
                    print(f"⚠️ 提取第{page_num+1}页文本失败: {e}")
                    continue
            
            doc.close()
            
            if not full_text.strip():
                print("❌ PDF文件没有可提取的文本内容")
                return False
            
            print(f"✅ 成功提取PDF文本，总长度: {len(full_text)} 字符")
            
            # 显示完整文本内容
            print(f"\n📋 完整文本内容:")
            print("-" * 50)
            print(full_text)
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ 文本提取失败: {e}")
            return False
        
        # 测试行程信息解析
        print(f"\n🔄 开始解析行程信息...")
        trips = parse_trip_info_from_text(full_text)
        
        if trips:
            print(f"✅ 成功解析到 {len(trips)} 个行程信息:")
            for i, trip in enumerate(trips, 1):
                print(f"  行程{i}: {trip}")
        else:
            print("❌ 未能解析到行程信息")
            
            # 尝试简单解析
            print(f"\n🔄 尝试简单解析...")
            lines = full_text.split('\n')
            simple_trips = parse_simple_trip_info(lines)
            
            if simple_trips:
                print(f"✅ 简单解析成功，解析到 {len(simple_trips)} 个行程信息:")
                for i, trip in enumerate(simple_trips, 1):
                    print(f"  行程{i}: {trip}")
            else:
                print("❌ 简单解析也失败")
                
                # 显示一些文本行用于调试
                print(f"\n🔍 调试信息 - 所有文本行:")
                for i, line in enumerate(lines, 1):
                    if line.strip():
                        print(f"  {i:2d}: '{line.strip()}'")
        
        # 测试完整的提取函数
        print(f"\n🔄 测试完整的提取函数...")
        extracted_trips = extract_trip_info_from_itinerary(full_path)
        
        if extracted_trips:
            print(f"✅ 完整提取成功，提取到 {len(extracted_trips)} 个行程信息:")
            for i, trip in enumerate(extracted_trips, 1):
                print(f"  行程{i}: {trip}")
        else:
            print("❌ 完整提取失败")
        
        return len(extracted_trips) > 0
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 行程信息提取功能测试（独立版本）")
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
    else:
        print("⚠️ 测试失败，需要调试解析逻辑")
        print("\n💡 建议：")
        print("   1. 检查PDF文件格式")
        print("   2. 调整正则表达式模式")
        print("   3. 查看提取的文本内容")
    
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
