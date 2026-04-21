import os
import zipfile
import hashlib
import json
import sys
from collections import deque
from pathlib import Path
import shutil
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

def _zipfile_open_read(zip_path):
    """打开只读 ZipFile；metadata_encoding 仅 Python 3.11+ 支持。"""
    if sys.version_info >= (3, 11):
        return zipfile.ZipFile(zip_path, 'r', metadata_encoding='gbk')
    return zipfile.ZipFile(zip_path, 'r')

def _zip_member_fs_name(member_name):
    """
    ZIP 成员名映射为用于创建本地路径的字符串。
    3.11+ 由 metadata_encoding='gbk' 已得到正确 Unicode；
    更早版本对常见「按 CP437 误解码的 GBK 字节」做还原。
    """
    if sys.version_info >= (3, 11):
        return member_name
    try:
        return member_name.encode('cp437').decode('gbk')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return member_name

def _is_zip_file_name(file_name):
    """判断文件名是否为ZIP。"""
    return Path(file_name).suffix.lower() == '.zip'

def _safe_target_path(extract_root, member_name):
    """
    生成安全目标路径，防止 Zip Slip 路径穿越。
    返回 Path 或 None。
    """
    safe_member = _zip_member_fs_name(member_name).replace('\\', '/')
    relative = Path(safe_member)
    if relative.is_absolute() or '..' in relative.parts:
        return None

    root_resolved = Path(extract_root).resolve()
    target = (root_resolved / relative).resolve()
    if target != root_resolved and root_resolved not in target.parents:
        return None
    return target

def _build_nested_extract_dir(zip_file_path):
    """
    为子ZIP生成唯一解压目录：xxx.zip -> xxx_unzipped / xxx_unzipped_2 ...
    """
    base = zip_file_path.with_suffix('')
    candidate = Path(f"{base}_unzipped")
    index = 2
    while candidate.exists():
        candidate = Path(f"{base}_unzipped_{index}")
        index += 1
    return candidate

def _extract_zip_once(zip_path, extract_dir, logger, max_files_per_zip, max_total_uncompressed, current_total_size):
    """
    仅解压一层ZIP，返回(本层解压出的文件Path列表, 本层解压字节数)。
    """
    extract_path = Path(extract_dir)
    extract_path.mkdir(parents=True, exist_ok=True)

    with _zipfile_open_read(zip_path) as zip_ref:
        infos = zip_ref.infolist()
        if len(infos) > max_files_per_zip:
            raise ValueError(f"ZIP条目过多({len(infos)})，超过限制({max_files_per_zip})")

        extracted_files = []
        layer_size = 0

        for info in infos:
            member_name = info.filename
            # 目录条目跳过
            if info.is_dir() or member_name.endswith('/'):
                continue

            target_path = _safe_target_path(extract_path, member_name)
            if target_path is None:
                logger.warning("检测到可疑ZIP成员路径，已跳过")
                continue

            # 预估解压总大小，防止压缩炸弹
            projected_size = current_total_size + layer_size + max(0, info.file_size)
            if projected_size > max_total_uncompressed:
                raise ValueError(
                    f"解压后总大小将超过限制({max_total_uncompressed} bytes)"
                )

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zip_ref.open(member_name) as src, target_path.open('wb') as dst:
                shutil.copyfileobj(src, dst)

            actual_size = target_path.stat().st_size
            layer_size += actual_size
            extracted_files.append(target_path)

    return extracted_files, layer_size

def extract_zip(zip_path, extract_dir):
    """递归解压ZIP到指定目录（支持子ZIP），并带基础安全限制。"""
    logger = current_app.logger

    # 可通过配置覆盖
    max_depth = int(current_app.config.get('ZIP_MAX_NESTED_DEPTH', 5))
    # <=0 表示不限制ZIP数量
    max_archives = int(current_app.config.get('ZIP_MAX_ARCHIVES', 0))
    max_files_per_zip = int(current_app.config.get('ZIP_MAX_FILES_PER_ARCHIVE', 10000))
    max_total_uncompressed = int(
        current_app.config.get('ZIP_MAX_TOTAL_UNCOMPRESSED_SIZE', 2 * 1024 * 1024 * 1024)
    )

    try:
        logger.info(f"开始递归解压ZIP: {zip_path} -> {extract_dir}")
    except Exception:
        logger.info("开始递归解压ZIP")

    try:
        queue = deque([(Path(zip_path), Path(extract_dir), 0)])
        visited_archives = set()
        extracted_total_files = 0
        extracted_total_size = 0
        processed_archives = 0

        while queue:
            current_zip, current_extract_dir, depth = queue.popleft()
            zip_key = str(current_zip.resolve())
            if zip_key in visited_archives:
                continue
            visited_archives.add(zip_key)

            if depth > max_depth:
                logger.warning(f"跳过超过最大层级的ZIP（depth={depth}, max={max_depth}）")
                continue

            if max_archives > 0 and processed_archives >= max_archives:
                raise ValueError(f"ZIP数量超过限制({max_archives})，已中止解压")

            if not current_zip.exists():
                logger.warning(f"ZIP文件不存在，跳过: {current_zip}")
                continue

            processed_archives += 1
            logger.info(f"解压第{processed_archives}个ZIP，层级={depth}: {current_zip}")

            extracted_files, layer_size = _extract_zip_once(
                current_zip,
                current_extract_dir,
                logger,
                max_files_per_zip,
                max_total_uncompressed,
                extracted_total_size
            )
            extracted_total_files += len(extracted_files)
            extracted_total_size += layer_size

            # 发现子ZIP继续入队
            for extracted_file in extracted_files:
                if _is_zip_file_name(extracted_file.name):
                    if depth >= max_depth:
                        logger.warning(f"发现子ZIP但已达最大层级，跳过: {extracted_file.name}")
                        continue
                    nested_extract_dir = _build_nested_extract_dir(extracted_file)
                    queue.append((extracted_file, nested_extract_dir, depth + 1))

        logger.info(
            f"递归解压完成，共处理ZIP {processed_archives} 个，解压文件 {extracted_total_files} 个，"
            f"累计大小 {extracted_total_size} bytes"
        )
    except Exception as e:
        logger.error(f"递归解压ZIP文件时发生错误: {str(e)}")
        raise

    return extract_dir

def extract_zip_for_raw_print(zip_path, extract_dir):
    """专门为原始打印解压ZIP文件，返回解压后的文件信息列表"""
    logger = current_app.logger
    
    try:
        logger.info(f"开始为原始打印解压ZIP文件: {zip_path}")
        
        # 先解压文件
        extract_zip(zip_path, extract_dir)
        
        # 获取解压后的文件信息
        extracted_files = []
        extract_path = Path(extract_dir)
        
        for file_path in extract_path.rglob('*'):
            if file_path.is_file():
                # 获取文件信息
                file_info = {
                    'name': file_path.name,  # 显示名称使用原始文件名
                    'filename': str(file_path.name),  # 存储名称也使用原始文件名
                    'file_path': str(file_path),
                    'relative_path': str(file_path.relative_to(extract_path)),
                    'size': file_path.stat().st_size,
                    'file_size': file_path.stat().st_size,
                    'type': get_file_type(file_path.name),
                    'file_type': get_file_type(file_path.name),
                    'extension': file_path.suffix.lower(),
                    'is_printable': is_printable_file(file_path.name)
                }
                extracted_files.append(file_info)
        
        logger.info(f"ZIP解压完成，共解压 {len(extracted_files)} 个文件")
        return extracted_files
        
    except Exception as e:
        logger.error(f"为原始打印解压ZIP文件时发生错误: {str(e)}")
        raise

def get_file_type(filename):
    """根据文件名获取文件类型"""
    if not filename:
        return 'unknown'
    
    ext = Path(filename).suffix.lower()
    
    # 图片文件
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
        return 'image'
    # PDF文件
    elif ext == '.pdf':
        return 'pdf'
    # 文档文件
    elif ext in ['.doc', '.docx', '.txt', '.rtf']:
        return 'document'
    # 表格文件
    elif ext in ['.xls', '.xlsx', '.csv']:
        return 'spreadsheet'
    # 压缩文件
    elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
        return 'archive'
    # 其他文件
    else:
        return 'other'

def is_printable_file(filename):
    """检查文件是否可打印"""
    if not filename:
        return False
    
    ext = Path(filename).suffix.lower()
    
    # 可打印的文件类型
    printable_extensions = [
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
        '.doc', '.docx', '.txt', '.rtf', '.xls', '.xlsx', '.csv'
    ]
    
    return ext in printable_extensions

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