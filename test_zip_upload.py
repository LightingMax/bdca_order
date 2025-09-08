#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试ZIP文件上传和解压功能
"""

import requests
import os
import zipfile
import tempfile

def create_test_zip():
    """创建一个测试ZIP文件"""
    print("📦 创建测试ZIP文件...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    # 创建一些测试文件
    test_files = [
        ("document1.pdf", "这是一个PDF文档的内容"),
        ("image1.jpg", "这是一个图片文件的内容"),
        ("report.docx", "这是一个Word文档的内容"),
        ("data.xlsx", "这是一个Excel文件的内容")
    ]
    
    # 创建文件
    for filename, content in test_files:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   ✅ 创建文件: {filename}")
    
    # 创建ZIP文件
    zip_path = os.path.join(temp_dir, "test_files.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for filename, _ in test_files:
            file_path = os.path.join(temp_dir, filename)
            zipf.write(file_path, filename)
    
    print(f"   ✅ 创建ZIP文件: {zip_path}")
    print(f"   📁 ZIP文件大小: {os.path.getsize(zip_path)} 字节")
    
    return zip_path

def test_zip_upload():
    """测试ZIP文件上传"""
    base_url = "http://192.168.20.95:12345"
    
    print("🧪 开始测试ZIP文件上传和解压...")
    print(f"📍 目标地址: {base_url}")
    print("-" * 50)
    
    # 创建测试ZIP文件
    zip_path = create_test_zip()
    
    try:
        # 上传ZIP文件
        print("\n📤 上传ZIP文件...")
        with open(zip_path, 'rb') as f:
            files = {'files': ('test_files.zip', f, 'application/zip')}
            data = {'is_raw_print': 'true'}
            
            response = requests.post(
                f"{base_url}/api/upload-raw",
                files=files,
                data=data,
                timeout=30
            )
        
        print(f"📊 上传响应状态码: {response.status_code}")
        print(f"📄 响应内容: {response.text[:500]}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ ZIP文件上传成功！")
                    
                    # 检查解压结果
                    extracted_files = result.get('extracted_files', [])
                    if extracted_files:
                        print(f"🎯 ZIP文件解压成功，解压出 {len(extracted_files)} 个文件:")
                        for i, file_info in enumerate(extracted_files, 1):
                            print(f"   {i}. {file_info.get('name', '未知')} "
                                  f"({file_info.get('type', '未知类型')}) "
                                  f"- {file_info.get('size', 0)} 字节")
                        
                        # 测试预览功能
                        if extracted_files:
                            test_file = extracted_files[0]
                            filename = test_file.get('name', '')
                            if filename:
                                print(f"\n👁️ 测试预览功能，文件: {filename}")
                                preview_response = requests.post(
                                    f"{base_url}/api/get-raw-file",
                                    json={'filename': filename},
                                    timeout=10
                                )
                                print(f"📊 预览响应状态码: {preview_response.status_code}")
                                print(f"📄 预览响应内容: {preview_response.text[:300]}")
                    else:
                        print("⚠️ ZIP文件上传成功，但没有解压后的文件信息")
                        print("   这可能意味着ZIP文件解压失败或没有内容")
                else:
                    print(f"❌ ZIP文件上传失败: {result.get('message', '未知错误')}")
            except Exception as e:
                print(f"❌ 解析响应失败: {str(e)}")
        else:
            print(f"❌ 上传请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
    
    finally:
        # 清理临时文件
        try:
            import shutil
            shutil.rmtree(os.path.dirname(zip_path))
            print("\n🧹 临时文件已清理")
        except Exception as e:
            print(f"⚠️ 清理临时文件失败: {str(e)}")
    
    print("-" * 50)
    print("🎯 ZIP文件测试完成！")

if __name__ == "__main__":
    test_zip_upload()
