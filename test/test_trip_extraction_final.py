0#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终版行程信息提取功能测试
"""

import os
import sys
import re
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def parse_trip_info_final(text):
    """
    最终版：基于实际PDF格式的解析
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
                
                # 读取服务商
                i += 1
                if i < len(lines):
                    trip['service_provider'] = lines[i].strip()
                
                # 读取车型
                i += 1
                if i < len(lines):
                    trip['car_type'] = lines[i].strip()
                
                # 读取上车时间
                i += 1
                if i < len(lines):
                    trip['pickup_time'] = lines[i].strip()
                
                # 读取城市
                i += 1
                if i < len(lines):
                    trip['city'] = lines[i].strip()
                
                # 读取起点（可能跨多行）
                i += 1
                if i < len(lines):
                    start_point = lines[i].strip()
                    i += 1
                    # 检查下一行是否是起点的延续
                    if i < len(lines) and not lines[i].strip().isdigit() and '元' not in lines[i] and '说明：' not in lines[i]:
                        start_point += lines[i].strip()
                        i += 1
                    trip['start_point'] = start_point
                
                # 读取终点（可能跨多行）
                if i < len(lines):
                    end_point = lines[i].strip()
                    i += 1
                    # 检查下一行是否是终点的延续
                    if i < len(lines) and not lines[i].strip().isdigit() and '元' not in lines[i] and '说明：' not in lines[i]:
                        end_point += lines[i].strip()
                        i += 1
                    trip['end_point'] = end_point
                
                # 读取金额
                if i < len(lines):
                    amount_line = lines[i].strip()
                    amount_match = re.search(r'(\d+\.?\d*)\s*元', amount_line)
                    if amount_match:
                        trip['amount'] = float(amount_match.group(1))
                    i += 1
                
                trips.append(trip)
                print(f"解析到行程: {trip}")
            else:
                i += 1
        
        return trips
        
    except Exception as e:
        print(f"最终版解析失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_trip_extraction():
    """测试行程信息提取功能"""
    print("🧪 测试行程信息提取功能（最终版）")
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
        
        # 测试最终版解析
        print(f"\n🔄 测试最终版解析...")
        trips = parse_trip_info_final(full_text)
        
        if trips:
            print(f"✅ 最终版解析成功，解析到 {len(trips)} 个行程信息:")
            for i, trip in enumerate(trips, 1):
                print(f"  行程{i}: {trip}")
        else:
            print("❌ 最终版解析失败")
            return False
        
        # 生成格式化的行程记录
        print(f"\n📋 格式化行程记录:")
        print("=" * 50)
        print("行程记录")
        print("=" * 50)
        for trip in trips:
            record = f"{trip['sequence']}, {trip['pickup_time']}, {trip['city']}, {trip['start_point']}, {trip['end_point']}, {trip['amount']:.2f}元"
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
    print("🚀 行程信息提取功能测试（最终版）")
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
        print("\n💡 现在可以将这个解析逻辑集成到主系统中")
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
