import os
import json
import uuid
import datetime
import hashlib
from flask import current_app, request

def get_user_mac():
    """获取用户唯一标识"""
    logger = current_app.logger
    logger.debug("尝试获取用户唯一标识")
    
    try:
        # 使用IP和用户代理作为标识
        ip = request.remote_addr or '127.0.0.1'
        user_agent = request.headers.get('User-Agent', '')
        
        # 创建一个基于IP和用户代理的唯一标识
        identifier = f"{ip}_{user_agent}"
        # 使用MD5哈希生成一个固定长度的标识符
        hash_id = hashlib.md5(identifier.encode()).hexdigest()
        logger.info(f"使用哈希标识符: {hash_id}")
        return hash_id
    
    except Exception as e:
        logger.error(f"获取用户标识出错: {str(e)}", exc_info=True)
        # 生成一个随机标识符作为后备
        random_id = f"unknown_{uuid.uuid4().hex[:12]}"
        logger.warning(f"使用随机标识符: {random_id}")
        return random_id

def load_user_data():
    """加载用户数据文件"""
    logger = current_app.logger
    user_data_file = current_app.config['USER_DATA_FILE']
    logger.debug(f"尝试加载用户数据文件: {user_data_file}")
    
    if os.path.exists(user_data_file):
        try:
            with open(user_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"成功加载用户数据，包含 {len(data.get('users', {}))} 个用户")
                return data
        except Exception as e:
            logger.error(f"读取用户数据文件出错: {str(e)}", exc_info=True)
    else:
        logger.warning(f"用户数据文件不存在: {user_data_file}")
    
    # 如果文件不存在或读取出错，返回初始结构
    logger.info("返回空的用户数据结构")
    return {"users": {}}

def save_user_data(mac_address, file_count, total_amount, order_ids):
    """保存用户打印信息"""
    logger = current_app.logger
    logger.info(f"保存用户数据: MAC={mac_address}, 文件数={file_count}, 总金额={total_amount}")
    
    data = load_user_data()
    
    # 获取当前时间
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 如果用户不存在，创建新用户
    if mac_address not in data["users"]:
        logger.info(f"创建新用户: {mac_address}")
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
    
    logger.debug(f"用户 {mac_address} 的累计打印次数: {data['users'][mac_address]['total_prints']}, 累计金额: {data['users'][mac_address]['total_amount']}")
    
    # 保存到文件
    try:
        with open(current_app.config['USER_DATA_FILE'], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("用户数据保存成功")
    except Exception as e:
        logger.error(f"保存用户数据出错: {str(e)}", exc_info=True)
    
    return data

def get_all_user_stats():
    """获取所有用户的统计数据"""
    logger = current_app.logger
    logger.info("获取所有用户的统计数据")
    
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
    
    logger.info(f"返回 {len(stats)} 个用户的统计数据")
    return stats 