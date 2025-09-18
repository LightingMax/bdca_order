#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import camelot
import pdfplumber
import pandas as pd

def test_camelot():
    print("=" * 60)
    print("CAMELOT-PY 测试")
    print("=" * 60)
    
    test_file = "temp_files/【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
    
    # 测试不同flavor
    flavors = ['lattice', 'stream']
    
    for flavor in flavors:
        print(f"\n🔍 使用camelot-py，flavor='{flavor}'")
        print(f"📊 参数: camelot.read_pdf('{test_file}', pages='1', flavor='{flavor}')")
        
        tables = camelot.read_pdf(test_file, pages='1', flavor=flavor)
        
        if tables:
            df = tables[0].df
            print(f"✅ 找到表格，形状: {df.shape}")
            print("📋 表格内容:")
            print(df)
        else:
            print("❌ 未找到表格")
        print("-" * 40)

def test_pdfplumber():
    print("=" * 60)
    print("PDFPLUMBER 测试")
    print("=" * 60)
    
    test_file = "temp_files/【及时用车-53.21元-2个行程】高德打车电子行程单.pdf"
    
    # 测试不同table_settings
    strategies = [
        {},
        {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
        {"vertical_strategy": "text", "horizontal_strategy": "text"},
        {"vertical_strategy": "lines", "horizontal_strategy": "text"},
        {"vertical_strategy": "text", "horizontal_strategy": "lines"},
    ]
    
    with pdfplumber.open(test_file) as pdf:
        page = pdf.pages[0]
        
        for i, settings in enumerate(strategies):
            print(f"\n🔍 使用pdfplumber，策略{i+1}")
            print(f"📊 参数: page.extract_tables(table_settings={settings})")
            
            tables = page.extract_tables(table_settings=settings)
            
            if tables:
                print(f"✅ 找到 {len(tables)} 个表格")
                for j, table in enumerate(tables):
                    print(f"📋 表格{j+1}内容:")
                    for k, row in enumerate(table):
                        print(f"第{k}行: {row}")
            else:
                print("❌ 未找到表格")
            print("-" * 40)

if __name__ == "__main__":
    test_camelot()
    test_pdfplumber()
