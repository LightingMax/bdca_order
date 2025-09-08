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
        return ip
    
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

def load_global_stats():
    """加载全局统计数据"""
    logger = current_app.logger
    global_stats_file = current_app.config.get('GLOBAL_STATS_FILE', 'global_stats.json')
    logger.debug(f"尝试加载全局统计数据文件: {global_stats_file}")
    
    if os.path.exists(global_stats_file):
        try:
            with open(global_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"成功加载全局统计数据，总行程单数: {data.get('total_itineraries', 0)}")
                return data
        except Exception as e:
            logger.error(f"读取全局统计数据文件出错: {str(e)}", exc_info=True)
    else:
        logger.warning(f"全局统计数据文件不存在: {global_stats_file}")
    
    # 如果文件不存在或读取出错，返回初始结构
    logger.info("返回空的全局数据结构")
    return {
        "total_itineraries": 0,
        "total_amount": 0.0,
        "first_run": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "last_update": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "run_count": 0
    }

def save_global_stats(itinerary_count, total_amount):
    """保存全局统计数据"""
    logger = current_app.logger
    logger.info(f"保存全局统计数据: 行程单数={itinerary_count}, 总金额={total_amount}")
    
    data = load_global_stats()
    
    # 更新统计数据
    data["total_itineraries"] += itinerary_count
    data["total_amount"] += total_amount
    data["last_update"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data["run_count"] += 1
    
    logger.info(f"全局统计更新: 累计行程单数={data['total_itineraries']}, 累计金额={data['total_amount']}, 运行次数={data['run_count']}")
    
    # 保存到文件
    global_stats_file = current_app.config.get('GLOBAL_STATS_FILE', 'global_stats.json')
    try:
        with open(global_stats_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("全局统计数据保存成功")
    except Exception as e:
        logger.error(f"保存全局统计数据出错: {str(e)}", exc_info=True)
    
    return data

def get_global_stats():
    """获取全局统计数据"""
    logger = current_app.logger
    logger.info("获取全局统计数据")
    
    data = load_global_stats()
    
    # 计算运行时长
    if data.get('first_run'):
        try:
            first_run = datetime.datetime.strptime(data['first_run'], '%Y-%m-%d %H:%M:%S')
            current_time = datetime.datetime.now()
            run_duration = current_time - first_run
            days = run_duration.days
            hours = run_duration.seconds // 3600
            minutes = (run_duration.seconds % 3600) // 60
            
            if days > 0:
                duration_str = f"{days}天{hours}小时{minutes}分钟"
            elif hours > 0:
                duration_str = f"{hours}小时{minutes}分钟"
            else:
                duration_str = f"{minutes}分钟"
                
            data['run_duration'] = duration_str
        except Exception as e:
            logger.warning(f"计算运行时长时出错: {e}")
            data['run_duration'] = "未知"
    
    logger.info(f"返回全局统计数据，总行程单数: {data.get('total_itineraries', 0)}")
    return data

# 🎉 彩蛋：直接运行此文件时显示统计信息
if __name__ == "__main__":
    print("🎉 订单报销系统 - 全局统计彩蛋 🎉")
    print("=" * 50)
    
    try:
        import os
        import json
        
        # 自动检测数据文件路径
        current_dir = os.path.abspath(os.path.dirname(__file__))
        project_root = current_dir
        
        # 向上查找，直到找到包含data目录的根目录
        while project_root != os.path.dirname(project_root):
            if os.path.exists(os.path.join(project_root, 'data')):
                break
            project_root = os.path.dirname(project_root)
        
        data_folder = os.path.join(project_root, 'data')
        user_data_file = os.path.join(data_folder, 'user_data.json')
        global_stats_file = os.path.join(data_folder, 'global_stats.json')
        
        print(f"🔍 数据路径: {data_folder}")
        
        # 读取用户统计数据
        print("\n📊 用户统计信息:")
        print("-" * 30)
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            
            users = user_data.get('users', {})
            if users:
                for i, (user_id, user_info) in enumerate(users.items(), 1):
                    print(f"{i}. 用户: {user_id}")
                    print(f"   总打印次数: {user_info.get('total_prints', 0)}")
                    print(f"   总金额: ¥{user_info.get('total_amount', 0):.2f}")
                    last_print = user_info.get('print_history', [{}])[-1].get('timestamp', '无') if user_info.get('print_history') else '无'
                    print(f"   最后打印: {last_print}")
                    print()
            else:
                print("暂无用户数据")
        else:
            print("用户数据文件不存在")
        
        # 读取全局统计数据
        print("\n🌍 全局统计信息:")
        print("-" * 30)
        if os.path.exists(global_stats_file):
            with open(global_stats_file, 'r', encoding='utf-8') as f:
                global_stats = json.load(f)
            
            print(f"累计行程单数: {global_stats.get('total_itineraries', 0)} 份")
            print(f"累计总金额: ¥{global_stats.get('total_amount', 0):.2f}")
            print(f"系统运行次数: {global_stats.get('run_count', 0)} 次")
            print(f"首次运行: {global_stats.get('first_run', '未知')}")
            print(f"最后更新: {global_stats.get('last_update', '未知')}")
            
            # 计算运行时长
            if global_stats.get('first_run'):
                try:
                    from datetime import datetime
                    first_run = datetime.strptime(global_stats['first_run'], '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.now()
                    run_duration = current_time - first_run
                    days = run_duration.days
                    hours = run_duration.seconds // 3600
                    minutes = (run_duration.seconds % 3600) // 60
                    
                    if days > 0:
                        duration_str = f"{days}天{hours}小时{minutes}分钟"
                    elif hours > 0:
                        duration_str = f"{hours}小时{minutes}分钟"
                    else:
                        duration_str = f"{minutes}分钟"
                    
                    print(f"系统运行时长: {duration_str}")
                except Exception as e:
                    print(f"系统运行时长: 计算失败 ({e})")
        else:
            print("全局统计文件不存在")
        
        print("\n" + "=" * 50)
        print("🎯 彩蛋提示: 每次上传文件后，系统会自动更新这些统计数据！")
        
    except Exception as e:
        print(f"❌ 获取统计信息时出错: {e}")
        import traceback
        traceback.print_exc()

def load_classification_stats():
    """加载分类统计数据"""
    logger = current_app.logger
    try:
        classification_stats_file = current_app.config.get('CLASSIFICATION_STATS_FILE', 'data/classification_stats.json')
        logger.debug(f"尝试加载分类统计数据文件: {classification_stats_file}")
        
        if os.path.exists(classification_stats_file):
            with open(classification_stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"成功加载分类统计数据: {data}")
                return data
        else:
            logger.warning("分类统计数据文件不存在，返回默认值")
            return {
                'taxi_amount': 0.0,
                'hotel_amount': 0.0,
                'total_amount': 0.0,
                'taxi_orders': 0,
                'hotel_orders': 0,
                'last_updated': None
            }
    except Exception as e:
        logger.error(f"加载分类统计数据出错: {str(e)}")
        return {
            'taxi_amount': 0.0,
            'hotel_amount': 0.0,
            'total_amount': 0.0,
            'taxi_orders': 0,
            'hotel_orders': 0,
            'last_updated': None
        }

def save_classification_stats(taxi_amount, hotel_amount, taxi_orders, hotel_orders):
    """保存分类统计数据"""
    logger = current_app.logger
    try:
        classification_stats_file = current_app.config.get('CLASSIFICATION_STATS_FILE', 'data/classification_stats.json')
        
        # 加载现有数据
        existing_data = load_classification_stats()
        
        # 累加金额和订单数
        new_data = {
            'taxi_amount': existing_data['taxi_amount'] + taxi_amount,
            'hotel_amount': existing_data['hotel_amount'] + hotel_amount,
            'total_amount': existing_data['taxi_amount'] + existing_data['hotel_amount'] + taxi_amount + hotel_amount,
            'taxi_orders': existing_data['taxi_orders'] + taxi_orders,
            'hotel_orders': existing_data['hotel_orders'] + hotel_orders,
            'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(classification_stats_file), exist_ok=True)
        
        # 保存数据
        with open(classification_stats_file, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分类统计数据保存成功: {new_data}")
        return new_data
        
    except Exception as e:
        logger.error(f"保存分类统计数据出错: {str(e)}")
        return None

def get_classification_stats():
    """获取分类统计数据"""
    return load_classification_stats() 