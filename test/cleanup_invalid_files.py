#!/usr/bin/env python3
"""
清理无效文件记录工具
清理file_hashes.json中results为空或输出文件不存在的记录
"""

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.file_service import cleanup_invalid_records, check_file_exists


def show_file_hashes_info():
    """显示文件哈希记录的统计信息"""
    app = create_app()
    
    with app.app_context():
        hash_file = os.path.join(app.config['DATA_FOLDER'], 'file_hashes.json')
        
        if not os.path.exists(hash_file):
            print("哈希记录文件不存在")
            return
        
        try:
            with open(hash_file, 'r', encoding='utf-8') as f:
                hashes = json.load(f)
        except Exception as e:
            print(f"读取哈希记录文件出错: {str(e)}")
            return
        
        total_records = len(hashes)
        empty_results_count = 0
        missing_files_count = 0
        valid_records_count = 0
        
        print(f"总记录数: {total_records}")
        print("\n详细统计:")
        
        for file_hash, file_info in hashes.items():
            filename = file_info.get('filename', 'unknown')
            results = file_info.get('results', [])
            
            if not results:
                empty_results_count += 1
                print(f"  ❌ {filename} (哈希: {file_hash[:16]}...) - results为空")
                continue
            
            # 检查输出文件是否存在
            all_files_exist = True
            for result in results:
                if 'output_file' in result:
                    output_file = os.path.join(app.config['OUTPUT_FOLDER'], result['output_file'])
                    if not os.path.exists(output_file):
                        all_files_exist = False
                        break
            
            if all_files_exist:
                valid_records_count += 1
                print(f"  ✅ {filename} (哈希: {file_hash[:16]}...) - {len(results)}个输出文件")
            else:
                missing_files_count += 1
                print(f"  ⚠️  {filename} (哈希: {file_hash[:16]}...) - 部分输出文件缺失")
        
        print(f"\n统计摘要:")
        print(f"  有效记录: {valid_records_count}")
        print(f"  results为空: {empty_results_count}")
        print(f"  文件缺失: {missing_files_count}")
        print(f"  需要清理: {empty_results_count + missing_files_count}")


def main():
    """主函数"""
    print("文件哈希记录清理工具")
    print("=" * 50)
    
    # 显示当前状态
    print("当前文件哈希记录状态:")
    show_file_hashes_info()
    
    # 询问是否清理
    print("\n" + "=" * 50)
    response = input("是否要清理无效记录？(y/N): ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("取消清理操作")
        return
    
    # 执行清理
    app = create_app()
    with app.app_context():
        cleaned_count = cleanup_invalid_records()
        
        if cleaned_count > 0:
            print(f"\n✅ 清理完成！删除了 {cleaned_count} 个无效记录")
            
            # 显示清理后的状态
            print("\n清理后的状态:")
            show_file_hashes_info()
        else:
            print("\n✅ 没有需要清理的记录")


if __name__ == "__main__":
    main()
