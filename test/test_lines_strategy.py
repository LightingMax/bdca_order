#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import requests
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfplumber

def call_qwen_api(table_data):
    """调用通义千问API规整表格数据"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": "Bearer sk-4b678a7de6d34b878356518397592170",
        "Content-Type": "application/json"
    }
    
    # 构建提示词
    prompt = f"""
请帮我整理以下行程记录：将它们按照上车时间升序排列并重新编号，然后以JSON格式返回结果。每个行程记录应包含序号、服务商、车型、上车时间、城市、起点、终点和金额等所有字段。请确保返回标准的JSON数组格式，无需添加任何额外解释。

原始表格数据：
{table_data}

请返回JSON数组格式，每个对象包含以下字段：
- sequence: 序号（字符串）
- service_provider: 服务商（字符串）
- car_type: 车型（字符串）
- pickup_time: 上车时间（字符串）
- city: 城市（字符串）
- start_point: 起点（字符串）
- end_point: 终点（字符串）
- amount: 金额（字符串）
"""
    
    data = {
        "model": "qwen2.5-32b-instruct",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        return f"API调用失败: {e}"

def test_pdfplumber_lines():
    print("=" * 60)
    print("PDFPLUMBER LINES策略测试")
    print("=" * 60)
    
    test_file = "temp_files/【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
    
    # 只使用lines策略
    strategies = [
        {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    ]
    
    with pdfplumber.open(test_file) as pdf:
        page = pdf.pages[0]
        
        for i, settings in enumerate(strategies):
            print(f"\n🔍 策略{i+1}: {settings}")
            print(f"📊 参数: page.extract_tables(table_settings={settings})")
            
            tables = page.extract_tables(table_settings=settings)
            
            if tables:
                print(f"✅ 找到 {len(tables)} 个表格")
                for j, table in enumerate(tables):
                    print(f"📋 表格{j+1}内容:")
                    for k, row in enumerate(table):
                        print(f"第{k}行: {row}")
                    
                    # 调用通义千问API规整数据
                    print(f"\n🤖 调用通义千问API规整表格{j+1}数据:")
                    result = call_qwen_api(table)
                    print(result)
                    
                    # 尝试解析JSON
                    try:
                        import re
                        # 提取JSON部分
                        json_match = re.search(r'\[.*\]', result, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            parsed_data = json.loads(json_str)
                            print(f"\n📊 解析后的结构化数据:")
                            for trip in parsed_data:
                                print(f"  - 序号: {trip['sequence']}, 服务商: {trip['service_provider']}, 时间: {trip['pickup_time']}, 起点: {trip['start_point']}, 终点: {trip['end_point']}, 金额: {trip['amount']}")
                    except Exception as e:
                        print(f"JSON解析失败: {e}")
            else:
                print("❌ 未找到表格")
            print("-" * 40)

if __name__ == "__main__":
    test_pdfplumber_lines()
