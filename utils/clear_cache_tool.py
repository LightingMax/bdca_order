#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存清理工具
用于删除智能处理的文件缓存，强制重新处理文件
"""

import os
import json
import shutil
from pathlib import Path

def clear_file_cache():
    """清理文件哈希缓存"""
    print("🧹 开始清理文件哈希缓存...")
    
    # 配置文件路径 - 相对于项目根目录
    data_folder = Path("../data")
    hash_file = data_folder / "file_hashes.json"
    
    if not hash_file.exists():
        print("ℹ️ 哈希缓存文件不存在，无需清理")
        return True
    
    try:
        # 备份原文件
        backup_file = data_folder / f"file_hashes_backup_{int(time.time())}.json"
        shutil.copy2(hash_file, backup_file)
        print(f"📋 已备份原缓存文件: {backup_file}")
        
        # 删除缓存文件
        hash_file.unlink()
        print("✅ 文件哈希缓存已删除")
        
        return True
    except Exception as e:
        print(f"❌ 清理缓存失败: {e}")
        return False

def clear_output_files():
    """清理输出文件"""
    print("\n🗂️ 开始清理输出文件...")
    
    output_folder = Path("../app/static/output")
    if not output_folder.exists():
        print("ℹ️ 输出文件夹不存在，无需清理")
        return True
    
    try:
        # 统计文件数量
        file_count = 0
        for file_path in output_folder.rglob("*.pdf"):
            file_path.unlink()
            file_count += 1
        
        print(f"✅ 已删除 {file_count} 个输出文件")
        return True
    except Exception as e:
        print(f"❌ 清理输出文件失败: {e}")
        return False

def clear_temp_files():
    """清理临时文件"""
    print("\n🗑️ 开始清理临时文件...")
    
    temp_folder = Path("../temp")
    if not temp_folder.exists():
        print("ℹ️ 临时文件夹不存在，无需清理")
        return True
    
    try:
        # 统计文件数量
        file_count = 0
        for file_path in temp_folder.rglob("*"):
            if file_path.is_file():
                file_path.unlink()
                file_count += 1
        
        print(f"✅ 已删除 {file_count} 个临时文件")
        return True
    except Exception as e:
        print(f"❌ 清理临时文件失败: {e}")
        return False

def clear_upload_cache():
    """清理上传缓存"""
    print("\n📤 开始清理上传缓存...")
    
    upload_folder = Path("../app/static/uploads")
    if not upload_folder.exists():
        print("ℹ️ 上传文件夹不存在，无需清理")
        return True
    
    try:
        # 统计文件数量
        file_count = 0
        for file_path in upload_folder.rglob("*"):
            if file_path.is_file():
                file_path.unlink()
                file_count += 1
        
        print(f"✅ 已删除 {file_count} 个上传缓存文件")
        return True
    except Exception as e:
        print(f"❌ 清理上传缓存失败: {e}")
        return False

def clear_smart_print_cache():
    """清理智能打印缓存"""
    print("\n🖨️ 开始清理智能打印缓存...")
    
    # 清理智能打印的输出文件
    output_folder = Path("../app/static/output")
    if output_folder.exists():
        try:
            file_count = 0
            for file_path in output_folder.rglob("*.pdf"):
                if "smart_combined" in file_path.name or "combined" in file_path.name:
                    file_path.unlink()
                    file_count += 1
            print(f"✅ 已删除 {file_count} 个智能打印输出文件")
        except Exception as e:
            print(f"⚠️ 清理智能打印输出文件失败: {e}")
    
    # 清理临时拼接文件
    temp_folder = Path("../temp")
    if temp_folder.exists():
        try:
            file_count = 0
            for file_path in temp_folder.rglob("*"):
                if file_path.is_file() and ("temp_" in file_path.name or "combined" in file_path.name):
                    file_path.unlink()
                    file_count += 1
            print(f"✅ 已删除 {file_count} 个临时拼接文件")
        except Exception as e:
            print(f"⚠️ 清理临时拼接文件失败: {e}")
    
    return True

def clear_all_cache():
    """清理所有缓存"""
    print("🚀 开始全面清理缓存...")
    print("=" * 50)
    
    success = True
    
    # 清理各种缓存
    if not clear_file_cache():
        success = False
    
    if not clear_output_files():
        success = False
    
    if not clear_temp_files():
        success = False
    
    if not clear_upload_cache():
        success = False
    
    if not clear_smart_print_cache():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 所有缓存清理完成！")
        print("\n💡 现在您可以：")
        print("   1. 重新上传ZIP文件到智能处理区域")
        print("   2. 系统将重新处理文件，不再使用缓存")
        print("   3. 智能打印功能将正常工作")
    else:
        print("⚠️ 部分缓存清理失败，请检查权限")
    
    return success

def selective_clear_cache():
    """选择性清理缓存"""
    print("🎯 选择性缓存清理")
    print("=" * 50)
    print("请选择要清理的缓存类型：")
    print("1. 文件哈希缓存（推荐）")
    print("2. 输出文件")
    print("3. 临时文件")
    print("4. 上传缓存")
    print("5. 智能打印缓存（推荐）")
    print("6. 清理所有缓存")
    print("0. 退出")
    
    while True:
        try:
            choice = input("\n请输入选择 (0-6): ").strip()
            
            if choice == "0":
                print("👋 退出缓存清理")
                break
            elif choice == "1":
                clear_file_cache()
                break
            elif choice == "2":
                clear_output_files()
                break
            elif choice == "3":
                clear_temp_files()
                break
            elif choice == "4":
                clear_upload_cache()
                break
            elif choice == "5":
                clear_smart_print_cache()
                break
            elif choice == "6":
                clear_all_cache()
                break
            else:
                print("❌ 无效选择，请输入 0-6")
        except KeyboardInterrupt:
            print("\n👋 用户中断，退出缓存清理")
            break
        except Exception as e:
            print(f"❌ 输入错误: {e}")

if __name__ == "__main__":
    import time
    
    print("🧹 智能处理缓存清理工具")
    print("=" * 50)
    print("此工具可以清理智能处理的缓存，解决文件重用问题")
    print("建议在遇到以下问题时使用：")
    print("• 文件显示'已上传过，重用了之前的处理结果'")
    print("• 智能打印功能异常")
    print("• 需要重新处理文件")
    print()
    
    try:
        choice = input("是否清理所有缓存？(y/n): ").strip().lower()
        
        if choice in ['y', 'yes', '是']:
            clear_all_cache()
        elif choice in ['n', 'no', '否']:
            selective_clear_cache()
        else:
            print("❌ 无效选择，默认清理所有缓存")
            clear_all_cache()
            
    except KeyboardInterrupt:
        print("\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
