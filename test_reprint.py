#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新打印功能测试脚本
"""

import requests
import json

def test_reprint_api():
    """测试重新打印API"""
    
    # 配置
    base_url = "http://localhost:12345"
    api_key = "TOKEN_PRINT_API_KEY_9527"
    
    print("=" * 50)
    print("重新打印功能测试")
    print("=" * 50)
    
    # 1. 获取文件哈希列表
    print("\n1. 获取文件哈希列表...")
    try:
        # 这里需要先上传一个文件来获取哈希值
        # 或者从现有的哈希文件中读取
        import os
        hash_file = os.path.join('data', 'file_hashes.json')
        
        if os.path.exists(hash_file):
            with open(hash_file, 'r', encoding='utf-8') as f:
                hashes = json.load(f)
            
            if hashes:
                file_hash = list(hashes.keys())[0]  # 使用第一个哈希值
                print(f"找到文件哈希: {file_hash}")
                
                # 2. 测试重新打印API
                print(f"\n2. 测试重新打印API...")
                reprint_url = f"{base_url}/api/reprint/{file_hash}"
                
                response = requests.post(reprint_url)
                print(f"请求URL: {reprint_url}")
                print(f"响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    if data.get('success'):
                        print("✅ 重新打印成功！")
                    else:
                        print(f"❌ 重新打印失败: {data.get('message')}")
                else:
                    print(f"❌ 请求失败: {response.text}")
            else:
                print("❌ 没有找到文件哈希记录")
        else:
            print("❌ 哈希文件不存在，请先上传文件")
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")


if __name__ == "__main__":
    test_reprint_api()


