import os
import json
import uuid
import datetime
from flask import current_app, request
from getmac import get_mac_address

def get_user_mac():
    """获取用户MAC地址"""
    try:
        # 尝试使用getmac库获取MAC地址
        mac = get_mac_address()
        if mac:
            return mac
        
        # 如果获取失败，使用IP和用户代理作为替代标识
        ip = request.remote_addr or '127.0.0.1'
        user_agent = request.headers.get('User-Agent', '')
        
        # 创建一个基于IP和用户代理的唯一标识
        identifier = f"{ip}_{user_agent}"
        # 使用MD5哈希生成一个固定长度的标识符
        import hashlib
        return hashlib.md5(identifier.encode()).hexdigest()
    
    except Exception as e:
        print(f"获取MAC地址出错: {str(e)}")
        # 生成一个随机标识符作为后备
        return f"unknown_{uuid.uuid4().hex[:12]}"

def load_user_data():
    """加载用户数据文件"""
    user_data_file = current_app.config['USER_DATA_FILE']
    
    if os.path.exists(user_data_file):
        try:
            with open(user_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取用户数据文件出错: {str(e)}")
    
    # 如果文件不存在或读取出错，返回初始结构
    return {"users": {}}

def save_user_data(mac_address, file_count, total_amount, order_ids):
    """保存用户打印信息"""
    data = load_user_data()
    
    # 获取当前时间
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 如果用户不存在，创建新用户
    if mac_address not in data["users"]:
        data["users"][mac_address] = {
            "print_history": [],
            "total_amount": 0,
            "total_prints": 0
        }
    
    # 添加新的打印记录
    data["users"][mac_address]["print_history"].append({
        "timestamp": timestamp,
        "file_count": file_count,
        "total_amount": total_amount,
        "order_ids": order_ids
    })
    
    # 更新总计
    data["users"][mac_address]["total_amount"] += total_amount
    data["users"][mac_address]["total_prints"] += file_count
    
    # 保存到文件
    try:
        with open(current_app.config['USER_DATA_FILE'], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存用户数据出错: {str(e)}")
    
    return data

def get_all_user_stats():
    """获取所有用户的统计数据"""
    data = load_user_data()
    
    stats = []
    for mac, user_data in data["users"].items():
        stats.append({
            "user_id": mac,
            "total_amount": user_data["total_amount"],
            "total_prints": user_data["total_prints"],
            "last_print": user_data["print_history"][-1]["timestamp"] if user_data["print_history"] else None
        })
    
    # 按总金额降序排序
    stats.sort(key=lambda x: x["total_amount"], reverse=True)
    
    return stats 