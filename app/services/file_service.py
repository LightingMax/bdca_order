import os
import zipfile
import hashlib
import json
import sys
from pathlib import Path
from flask import current_app

# 强制设置文件系统编码为UTF-8
if sys.platform.startswith('win'):
    # Windows系统特殊处理
    import locale
    try:
        # 尝试设置控制台编码为UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def allowed_file(filename):
    """检查文件是否为允许的类型"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def extract_zip(zip_path, extract_dir):
    """解压ZIP文件到指定目录，支持中文编码 - 使用pathlib库"""
    logger = current_app.logger
    
    # 安全地记录日志，避免编码问题
    try:
        logger.info(f"开始解压文件: {zip_path} 到 {extract_dir}")
    except Exception:
        logger.info("开始解压ZIP文件")
    
    # 转换为Path对象
    extract_path = Path(extract_dir)
    extract_path.mkdir(parents=True, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取所有文件名列表
            name_list = zip_ref.namelist()
            logger.info(f"ZIP文件中包含 {len(name_list)} 个文件")
            
            # 首先创建所有必要的目录
            directories_to_create = set()
            for file_name in name_list:
                if file_name.endswith('/'):
                    # 这是一个目录条目
                    continue
                
                # 获取文件的目录路径
                file_dir = Path(file_name).parent
                if file_dir != Path('.'):
                    directories_to_create.add(str(file_dir))
            
            # 创建所有必要的目录
            for dir_path in directories_to_create:
                try:
                    full_dir_path = extract_path / dir_path
                    full_dir_path.mkdir(parents=True, exist_ok=True)
                    logger.debug(f"创建目录: {dir_path}")
                except Exception as e:
                    logger.warning(f"创建目录失败 {dir_path}: {e}")
            
            # 遍历处理每个文件（跳过目录条目）
            extracted_count = 0
            for file_name in name_list:
                # 跳过目录条目
                if file_name.endswith('/'):
                    logger.debug(f"跳过目录条目: {file_name}")
                    continue
                
                try:
                    # 安全地处理文件名，避免编码问题
                    decoded_name = None
                    
                    # 方法1: 尝试直接使用原始名称
                    try:
                        decoded_name = file_name
                        # 测试路径是否可以正常构建
                        test_path = extract_path / decoded_name
                        # 如果到这里没有异常，说明原始名称可以使用
                        logger.debug("使用原始文件名")
                    except Exception:
                        decoded_name = None
                    
                    # 方法2: 如果原始名称有问题，尝试不同编码
                    if decoded_name is None:
                        encodings = ['utf-8', 'gbk', 'gb2312', 'cp437']
                        for encoding in encodings:
                            try:
                                decoded_name = file_name.encode('cp437').decode(encoding)
                                logger.debug(f"使用 {encoding} 解码文件名")
                                break
                            except UnicodeDecodeError:
                                continue
                    
                    # 方法3: 如果所有方法都失败，生成安全的文件名
                    if decoded_name is None:
                        # 生成安全的文件名
                        safe_chars = []
                        for c in file_name:
                            if c.isalnum() or c in '._-()':
                                safe_chars.append(c)
                            else:
                                safe_chars.append('_')
                        
                        safe_name = ''.join(safe_chars)
                        if not safe_name:
                            safe_name = f"file_{extracted_count}"
                        
                        decoded_name = safe_name
                        logger.warning("无法解码文件名，使用安全名称")
                    
                    # 提取文件
                    data = zip_ref.read(file_name)
                    
                    # 使用pathlib构建目标路径
                    target_path = extract_path / decoded_name
                    
                    # 写入文件（目录已经创建好了）
                    target_path.write_bytes(data)
                    
                    extracted_count += 1
                    logger.debug("成功解压文件")
                        
                except Exception as e:
                    # 完全避免在日志中包含可能有问题的文件名
                    error_msg = str(e)
                    if 'charmap' in error_msg or 'encode' in error_msg:
                        logger.error("解压文件时遇到编码问题，跳过此文件")
                    else:
                        logger.error(f"解压文件时出错: {error_msg}")
                    
                    # 如果单个文件解压失败，继续处理其他文件
                    continue
        
        logger.info(f"文件解压完成，共处理 {extracted_count} 个文件")
    except Exception as e:
        logger.error(f"解压ZIP文件时发生错误: {str(e)}")
        raise
    
    return extract_dir

def get_file_paths(directory):
    """获取目录中所有文件的路径 - 使用pathlib库"""
    directory_path = Path(directory)
    file_paths = []
    
    for file_path in directory_path.rglob('*'):
        if file_path.is_file():
            file_paths.append(str(file_path))
    
    current_app.logger.info(f"在目录 {directory} 中找到 {len(file_paths)} 个文件")
    return file_paths

def group_files_by_type(file_paths):
    """按文件类型对文件进行分组"""
    pdf_files = []
    xml_files = []
    other_files = []
    
    for file_path in file_paths:
        file_path_obj = Path(file_path)
        ext = file_path_obj.suffix.lower()
        if ext == '.pdf':
            pdf_files.append(file_path)
        elif ext == '.xml':
            xml_files.append(file_path)
        else:
            other_files.append(file_path)
    
    current_app.logger.info(f"文件分组结果: PDF={len(pdf_files)}个, XML={len(xml_files)}个, 其他={len(other_files)}个")
    
    return {
        'pdf': pdf_files,
        'xml': xml_files,
        'other': other_files
    }

def calculate_file_hash(file_path):
    """计算文件的SHA-256哈希值 - 使用pathlib库"""
    logger = current_app.logger
    logger.debug(f"计算文件哈希: {file_path}")
    
    file_path_obj = Path(file_path)
    hash_sha256 = hashlib.sha256()
    
    with file_path_obj.open('rb') as f:
        # 每次读取4MB数据进行哈希计算，避免一次性读取大文件
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            hash_sha256.update(chunk)
    
    file_hash = hash_sha256.hexdigest()
    logger.debug(f"文件哈希值: {file_hash}")
    return file_hash

def save_file_hash(file_hash, file_info):
    """保存文件哈希记录 - 使用pathlib库"""
    logger = current_app.logger
    hash_file = Path(current_app.config['DATA_FOLDER']) / 'file_hashes.json'
    
    # 加载现有哈希记录
    hashes = {}
    if hash_file.exists():
        try:
            with hash_file.open('r', encoding='utf-8') as f:
                hashes = json.load(f)
        except Exception as e:
            logger.error(f"读取哈希记录文件出错: {str(e)}")
    
    # 添加新记录
    hashes[file_hash] = file_info
    
    # 保存更新后的记录
    try:
        with hash_file.open('w', encoding='utf-8') as f:
            json.dump(hashes, f, ensure_ascii=False, indent=2)
        logger.info(f"文件哈希记录已保存: {file_hash}")
    except Exception as e:
        logger.error(f"保存哈希记录文件出错: {str(e)}")

def check_file_exists(file_hash):
    """检查文件是否已上传过（通过哈希值）- 使用pathlib库"""
    logger = current_app.logger
    hash_file = Path(current_app.config['DATA_FOLDER']) / 'file_hashes.json'
    
    # 如果哈希记录文件不存在，说明没有上传过任何文件
    if not hash_file.exists():
        logger.debug("哈希记录文件不存在，文件未上传过")
        return None
    
    # 加载哈希记录
    try:
        with hash_file.open('r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return None
    
    # 检查哈希值是否存在
    if file_hash in hashes:
        file_info = hashes[file_hash]
        
        # 检查文件完整性：如果results为空，说明之前的处理失败了
        if not file_info.get('results'):
            logger.warning(f"文件 {file_hash} 的记录存在但results为空，之前的处理可能失败了")
            return None
        
        # 检查输出文件是否真的存在
        results = file_info.get('results', [])
        all_files_exist = True
        
        for result in results:
            if 'output_file' in result:
                output_file = Path(current_app.config['OUTPUT_FOLDER']) / result['output_file']
                if not output_file.exists():
                    logger.warning(f"输出文件不存在: {output_file}")
                    all_files_exist = False
        
        if not all_files_exist:
            logger.warning(f"文件 {file_hash} 的部分输出文件不存在，需要重新处理")
            return None
        
        logger.info(f"文件已上传过且输出文件完整: {file_hash}")
        return file_info
    else:
        logger.debug(f"文件未上传过: {file_hash}")
        return None


def cleanup_invalid_records():
    """清理无效的文件记录（results为空或输出文件不存在的记录）- 使用pathlib库"""
    logger = current_app.logger
    hash_file = Path(current_app.config['DATA_FOLDER']) / 'file_hashes.json'
    
    if not hash_file.exists():
        logger.debug("哈希记录文件不存在，无需清理")
        return 0
    
    try:
        with hash_file.open('r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return 0
    
    cleaned_count = 0
    valid_hashes = {}
    
    for file_hash, file_info in hashes.items():
        # 检查results是否为空
        if not file_info.get('results'):
            logger.info(f"清理无效记录（results为空）: {file_hash}")
            cleaned_count += 1
            continue
        
        # 检查输出文件是否存在
        results = file_info.get('results', [])
        all_files_exist = True
        
        for result in results:
            if 'output_file' in result:
                output_file = Path(current_app.config['OUTPUT_FOLDER']) / result['output_file']
                if not output_file.exists():
                    logger.info(f"清理无效记录（输出文件不存在）: {file_hash}, 文件: {result['output_file']}")
                    all_files_exist = False
                    break
        
        if all_files_exist:
            valid_hashes[file_hash] = file_info
        else:
            cleaned_count += 1
    
    # 保存清理后的记录
    try:
        with hash_file.open('w', encoding='utf-8') as f:
            json.dump(valid_hashes, f, ensure_ascii=False, indent=2)
        logger.info(f"清理完成，删除了 {cleaned_count} 个无效记录")
    except Exception as e:
        logger.error(f"保存清理后的哈希记录文件出错: {str(e)}")
    
    return cleaned_count

def check_order_processed(order_id):
    """检查订单是否已处理过"""
    logger = current_app.logger
    hash_file = Path(current_app.config['DATA_FOLDER']) / 'file_hashes.json'
    
    # 如果哈希记录文件不存在，说明没有处理过任何订单
    if not hash_file.exists():
        logger.debug(f"哈希记录文件不存在，订单 {order_id} 未处理过")
        return False
    
    # 加载哈希记录
    try:
        with hash_file.open('r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return False
    
    # 遍历所有文件记录，检查是否存在该订单ID
    for file_hash, file_info in hashes.items():
        if 'results' in file_info:
            for result in file_info['results']:
                if result.get('order_id') == order_id:
                    logger.info(f"订单 {order_id} 已处理过，在文件 {file_info.get('filename', '未知')} 中")
                    return True
    
    logger.debug(f"订单 {order_id} 未处理过")
    return False

def get_processed_orders():
    """获取所有已处理过的订单ID列表"""
    logger = current_app.logger
    hash_file = Path(current_app.config['DATA_FOLDER']) / 'file_hashes.json'
    
    # 如果哈希记录文件不存在，返回空列表
    if not hash_file.exists():
        logger.debug("哈希记录文件不存在，返回空订单列表")
        return []
    
    # 加载哈希记录
    try:
        with hash_file.open('r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return []
    
    # 收集所有订单ID
    processed_orders = set()
    for file_hash, file_info in hashes.items():
        if 'results' in file_info:
            for result in file_info['results']:
                if 'order_id' in result:
                    processed_orders.add(result['order_id'])
    
    logger.info(f"找到 {len(processed_orders)} 个已处理过的订单")
    return list(processed_orders)


def update_file_print_status(file_hash, print_status, print_time=None):
    """更新文件的打印状态"""
    logger = current_app.logger
    hash_file = Path(current_app.config['DATA_FOLDER']) / 'file_hashes.json'
    
    # 如果哈希记录文件不存在，返回False
    if not hash_file.exists():
        logger.warning("哈希记录文件不存在，无法更新打印状态")
        return False
    
    # 加载哈希记录
    try:
        with hash_file.open('r', encoding='utf-8') as f:
            hashes = json.load(f)
    except Exception as e:
        logger.error(f"读取哈希记录文件出错: {str(e)}")
        return False
    
    # 检查文件是否存在
    if file_hash not in hashes:
        logger.warning(f"文件哈希 {file_hash} 不存在，无法更新打印状态")
        return False
    
    # 更新打印状态
    hashes[file_hash]['print_status'] = print_status
    if print_time:
        hashes[file_hash]['last_print_time'] = print_time
    
    # 保存更新后的记录
    try:
        with hash_file.open('w', encoding='utf-8') as f:
            json.dump(hashes, f, ensure_ascii=False, indent=2)
        logger.info(f"文件 {file_hash} 的打印状态已更新为: {print_status}")
        return True
    except Exception as e:
        logger.error(f"保存哈希记录文件出错: {str(e)}")
        return False 