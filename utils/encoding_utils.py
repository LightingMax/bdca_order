#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码检测工具模块
用于检测文件编码和文本编码
"""

import chardet
import os
from typing import Optional, Dict, Any

def detect_file_encoding(file_path: str) -> Dict[str, Any]:
    """
    检测文件编码
    
    Args:
        file_path: 文件路径
        
    Returns:
        包含编码信息的字典
    """
    try:
        # 读取文件的前几个字节来检测编码
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # 读取前10KB
        
        # 使用chardet检测编码
        result = chardet.detect(raw_data)
        
        return {
            'encoding': result.get('encoding', 'unknown'),
            'confidence': result.get('confidence', 0.0),
            'language': result.get('language', 'unknown')
        }
    except Exception as e:
        return {
            'encoding': 'unknown',
            'confidence': 0.0,
            'language': 'unknown',
            'error': str(e)
        }

def detect_text_encoding(text_bytes: bytes) -> Dict[str, Any]:
    """
    检测文本字节的编码
    
    Args:
        text_bytes: 文本字节数据
        
    Returns:
        包含编码信息的字典
    """
    try:
        result = chardet.detect(text_bytes)
        return {
            'encoding': result.get('encoding', 'unknown'),
            'confidence': result.get('confidence', 0.0),
            'language': result.get('language', 'unknown')
        }
    except Exception as e:
        return {
            'encoding': 'unknown',
            'confidence': 0.0,
            'language': 'unknown',
            'error': str(e)
        }

def read_file_with_encoding(file_path: str, encoding: Optional[str] = None) -> str:
    """
    使用指定编码读取文件
    
    Args:
        file_path: 文件路径
        encoding: 指定编码，如果为None则自动检测
        
    Returns:
        文件内容字符串
    """
    if encoding is None:
        # 自动检测编码
        encoding_info = detect_file_encoding(file_path)
        encoding = encoding_info.get('encoding', 'utf-8')
        print(f"检测到文件编码: {encoding} (置信度: {encoding_info.get('confidence', 0):.2f})")
    
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # 如果指定编码失败，尝试其他常见编码
        common_encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin1']
        for enc in common_encodings:
            if enc != encoding:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        print(f"使用备用编码 {enc} 成功读取文件")
                        return f.read()
                except UnicodeDecodeError:
                    continue
        
        # 如果所有编码都失败，使用错误处理
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            print(f"使用编码 {encoding} 和错误处理读取文件")
            return f.read()

def test_encodings():
    """测试编码检测功能"""
    print("=== 编码检测工具测试 ===")
    
    # 测试文件
    test_file = '../temp_files/ dzfp_25114000000003462819_杭州大数云智科技有限公司_20250831201746.pdf'
    
    if os.path.exists(test_file):
        print(f"测试文件: {test_file}")
        
        # 检测文件编码
        encoding_info = detect_file_encoding(test_file)
        print(f"检测结果: {encoding_info}")
        
        # 尝试读取文件
        try:
            content = read_file_with_encoding(test_file)
            print(f"文件内容长度: {len(content)} 字符")
            print(f"内容预览: {content[:200]}...")
        except Exception as e:
            print(f"读取文件失败: {e}")
    else:
        print(f"测试文件不存在: {test_file}")

if __name__ == '__main__':
    test_encodings()
