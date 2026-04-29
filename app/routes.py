import os
import uuid
import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, session, send_from_directory
from werkzeug.utils import secure_filename

from app.services.file_service import (
    allowed_file, extract_zip, extract_zip_for_raw_print, calculate_file_hash, 
    check_file_exists, save_file_hash, check_order_processed,
    get_processed_orders, update_file_print_status
)
from app.services.pdf_service import process_pdf_files
from app.services.print_service import print_pdf, prepare_raw_pdf_for_a4_print
from app.services.user_service import get_user_mac, save_user_data, get_all_user_stats, save_global_stats

main_bp = Blueprint('main', __name__)


def _looks_like_flight_upload(filename):
    """判断上传文件是否疑似机票，避免旧缓存把机票当普通发票复用。"""
    name = (filename or '').lower()
    return any(keyword in name for keyword in ['机票', '航班', '飞机票', '航空', '飞猪', 'flight', 'air ticket'])


def _should_reprocess_upload(filename):
    """对近期修正过识别逻辑的类型跳过旧缓存，避免历史结果污染。"""
    name = (filename or '').lower()
    hotel_keywords = ['华住', '酒店', '住宿', '结账单', '账单', 'hotel', 'accommodation', 'bill']
    return _looks_like_flight_upload(filename) or any(keyword in name for keyword in hotel_keywords)

@main_bp.route('/')
def index():
    """渲染主页"""
    current_app.logger.debug("访问主页")
    return render_template('index.html')

@main_bp.route('/statistics')
def statistics():
    """渲染统计页面"""
    current_app.logger.debug("访问统计页面")
    return render_template('statistics.html')

@main_bp.route('/api/upload', methods=['POST'])
def upload_file():
    """处理ZIP文件上传（智能处理功能）"""
    logger = current_app.logger
    logger.info("收到ZIP文件上传请求（智能处理）")
    
    # 检查是否有文件
    if 'files' not in request.files:
        logger.warning("上传请求中没有文件")
        return jsonify({'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    
    # 检查是否有文件被选择
    if len(files) == 0 or files[0].filename == '':
        logger.warning("上传的文件名为空")
        return jsonify({'error': '没有选择文件'}), 400
    
    # 生成唯一的临时目录
    session_id = str(uuid.uuid4())
    logger.info(f"创建会话: {session_id}")
    
    temp_folder = os.path.join(current_app.config['TEMP_FOLDER'], session_id)
    os.makedirs(temp_folder, exist_ok=True)
    
    extract_dir = os.path.join(temp_folder, 'extracted')
    os.makedirs(extract_dir, exist_ok=True)
    
    # 获取已处理过的订单ID列表
    processed_order_ids = set(get_processed_orders())
    logger.info(f"已处理过的订单数量: {len(processed_order_ids)}")
    
    all_results = []       # 所有处理结果（包括重用的）
    new_results = []       # 只包含新处理的结果
    processed_files = []
    reused_files = []
    
    try:
        logger.info(f"开始处理 {len(files)} 个上传的ZIP文件")
        
        for file in files:
            # 检查文件类型
            if not allowed_file(file.filename):
                logger.warning(f"不支持的文件类型: {file.filename}")
                continue
                
            # 保存原始文件名用于显示
            original_filename = file.filename
            # 保存文件
            filename = secure_filename(file.filename)
            zip_path = os.path.join(temp_folder, filename)
            file.save(zip_path)
            logger.info(f"文件已保存到: {zip_path}")
            logger.info(f"原始文件名: {original_filename}, 安全文件名: {filename}")
            
            # 计算文件哈希
            file_hash = calculate_file_hash(zip_path)
            logger.info(f"文件 {filename} 的哈希值: {file_hash}")
            
            # 获取会话级别的已处理文件哈希列表
            session_processed_hashes = session.get('processed_file_hashes', [])
            
            # 检查文件是否在当前会话中已上传过
            if file_hash in session_processed_hashes and not _should_reprocess_upload(original_filename):
                # 从全局存储中获取文件信息
                existing_file = check_file_exists(file_hash)
                if existing_file and 'results' in existing_file:
                    logger.info(f"文件 {filename} 在当前会话中已上传过，重用之前的处理结果")
                    # 将已有结果添加到总结果中
                    all_results.extend(existing_file['results'])
                    
                    # 将重用结果也添加到新结果中，确保前端能正确显示
                    reused_results = existing_file['results']
                    new_results.extend(reused_results)
                    
                    # 重新分析XML缺失情况，而不是直接重用之前的警告
                    # 为每个ZIP文件创建单独的提取目录
                    file_extract_dir = os.path.join(extract_dir, os.path.splitext(filename)[0])
                    os.makedirs(file_extract_dir, exist_ok=True)
                    
                    # 重新解压并分析文件
                    try:
                        if filename.lower().endswith('.zip'):
                            extract_zip(zip_path, file_extract_dir)
                        elif filename.lower().endswith('.pdf'):
                            import shutil
                            shutil.copy2(zip_path, os.path.join(file_extract_dir, filename))
                        else:
                            logger.warning(f"不支持的文件类型，跳过重新分析: {filename}")
                            raise ValueError(f"不支持的文件类型: {filename}")
                        
                        # 重新分析PDF文件，获取最新的XML缺失警告和分类统计（使用原始文件名）
                        original_filename = existing_file.get('original_filename', filename)
                        _, current_xml_warnings, current_classification_info = process_pdf_files(file_extract_dir, original_filename)
                        
                        reused_files.append({
                            'filename': filename,
                            'original_filename': existing_file.get('original_filename', filename),  # 使用保存的原始文件名
                            'hash': file_hash,
                            'original_upload_time': existing_file.get('upload_time', '未知'),
                            'result_count': len(existing_file['results']),
                            'print_status': existing_file.get('print_status', 'unknown'),  # 添加打印状态
                            'last_print_time': existing_file.get('last_print_time', '未打印'),
                            'xml_missing_warnings': current_xml_warnings,  # 使用最新的XML缺失警告
                            'classification_info': current_classification_info  # 使用最新的分类统计信息
                        })
                        
                        logger.info(f"文件 {filename} 重新分析完成，当前XML缺失警告数: {len(current_xml_warnings)}")
                        continue
                        
                    except Exception as e:
                        logger.error(f"重新分析文件 {filename} 时出错: {str(e)}")
                        # 如果重新分析失败，使用之前的数据
                        reused_files.append({
                            'filename': filename,
                            'original_filename': existing_file.get('original_filename', filename),  # 使用保存的原始文件名
                            'hash': file_hash,
                            'original_upload_time': existing_file.get('upload_time', '未知'),
                            'result_count': len(existing_file['results']),
                            'print_status': existing_file.get('print_status', 'unknown'),
                            'last_print_time': existing_file.get('last_print_time', '未打印'),
                            'xml_missing_warnings': existing_file.get('xml_missing_warnings', []),
                            'classification_info': existing_file.get('classification_info', {
                                'taxi_amount': 0,
                                'hotel_amount': 0,
                                'train_amount': 0,
                                'flight_amount': 0,
                                'total_amount': 0,
                                'taxi_orders': 0,
                                'hotel_orders': 0,
                                'train_tickets': 0,
                                'flight_tickets': 0,
                                'train_groups': 0,
                                'taxi_warnings': [],
                                'hotel_warnings': []
                            })
                        })
                        continue
                else:
                    logger.warning(f"文件 {filename} 在全局存储中不存在或处理结果无效，将重新处理")
            else:
                if file_hash in session_processed_hashes:
                    logger.info(f"文件 {filename} 属于需重新识别类型，跳过旧缓存并按最新逻辑重新处理")
                else:
                    logger.info(f"文件 {filename} 在当前会话中首次上传，将进行处理")
            
            # 为每个上传文件创建单独的提取目录
            file_extract_dir = os.path.join(extract_dir, os.path.splitext(filename)[0])
            os.makedirs(file_extract_dir, exist_ok=True)
            
            # 处理文件：ZIP 解压 / PDF 直存
            try:
                if filename.lower().endswith('.zip'):
                    extract_zip(zip_path, file_extract_dir)
                elif filename.lower().endswith('.pdf'):
                    # 兼容火车票“直接上传 PDF（非 zip）”
                    import shutil
                    shutil.copy2(zip_path, os.path.join(file_extract_dir, filename))
                else:
                    logger.warning(f"不支持的文件类型，跳过: {filename}")
                    continue
                
                # 处理PDF文件（使用原始文件名进行类型识别）
                results, xml_missing_warnings, classification_info = process_pdf_files(file_extract_dir, original_filename)
                
                # 过滤结果，找出新的订单
                file_new_results = []
                for result in results:
                    order_id = result.get('order_id')
                    if order_id and order_id not in processed_order_ids:
                        file_new_results.append(result)
                        processed_order_ids.add(order_id)  # 添加到已处理列表中
                        new_results.append(result)  # 记录新处理的结果
                
                # 添加所有结果到总结果列表
                all_results.extend(results)
                
                # 保存文件哈希和处理结果
                file_info = {
                    'filename': filename,
                    'original_filename': original_filename,  # 保存原始文件名
                    'upload_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'session_id': session_id,
                    'results': results
                }
                save_file_hash(file_hash, file_info)
                
                # 将文件哈希添加到会话级别的已处理列表中
                if file_hash not in session_processed_hashes:
                    session_processed_hashes.append(file_hash)
                    session['processed_file_hashes'] = session_processed_hashes
                
                processed_files.append({
                    'filename': filename,
                    'original_filename': original_filename,  # 添加原始文件名用于前端显示
                    'hash': file_hash,
                    'result_count': len(results),
                    'new_result_count': len(file_new_results),
                    'xml_missing_warnings': xml_missing_warnings,  # 保存XML缺失警告
                    'classification_info': classification_info  # 保存分类统计信息
                })
                
                logger.info(f"文件 {filename} 处理完成，订单总数: {len(results)}，新订单数: {len(file_new_results)}")
                
            except Exception as e:
                logger.error(f"处理文件 {filename} 时出错: {str(e)}", exc_info=True)
                # 如果一个ZIP文件处理失败，继续处理其他文件
                continue
        
        # 检查是否有任何结果（包括重用的）
        if not all_results and not reused_files:
            logger.warning("没有成功处理任何订单")
            return jsonify({'error': '没有成功处理任何订单'}), 400
            
        # 获取用户MAC地址
        mac_address = get_user_mac()
        logger.info(f"用户MAC地址: {mac_address}")
        
        # 保存用户数据（只记录新处理的订单）
        if new_results:
            total_new_amount = sum(result.get('amount', 0) for result in new_results)
            save_user_data(mac_address, len(new_results), total_new_amount, [result.get('order_id') for result in new_results])
            logger.info(f"用户数据已保存，新订单数: {len(new_results)}, 新增金额: {total_new_amount}")
        else:
            logger.info("没有新处理的订单，不更新用户统计数据")
        
        # 收集所有XML缺失警告
        all_xml_warnings = []
        all_files = processed_files + reused_files
        for file_result in all_files:
            if 'xml_missing_warnings' in file_result:
                all_xml_warnings.extend(file_result['xml_missing_warnings'])
        
        # 计算本次新增的分类统计（包括新处理和重用的文件）
        current_taxi_amount = 0
        current_hotel_amount = 0
        current_train_amount = 0
        current_flight_amount = 0
        current_taxi_orders = 0
        current_hotel_orders = 0
        current_train_tickets = 0
        current_flight_tickets = 0
        current_train_groups = 0
        current_taxi_warnings = []
        current_hotel_warnings = []
        
        # 聚合所有文件的分类统计信息（包括新处理和重用的文件）
        for file_result in all_files:
            if 'classification_info' in file_result:
                info = file_result['classification_info']
                current_taxi_amount += info.get('taxi_amount', 0)
                current_hotel_amount += info.get('hotel_amount', 0)
                current_train_amount += info.get('train_amount', 0)
                current_flight_amount += info.get('flight_amount', 0)
                current_taxi_orders += info.get('taxi_orders', 0)
                current_hotel_orders += info.get('hotel_orders', 0)
                current_train_tickets += info.get('train_tickets', 0)
                current_flight_tickets += info.get('flight_tickets', 0)
                current_train_groups += info.get('train_groups', 0)
                current_taxi_warnings.extend(info.get('taxi_warnings', []))
                current_hotel_warnings.extend(info.get('hotel_warnings', []))
        
        # 构建分类统计信息（只返回本次处理的数据，累计由前端维护）
        all_classification_info = {
            'taxi_amount': current_taxi_amount,
            'hotel_amount': current_hotel_amount,
            'train_amount': current_train_amount,
            'flight_amount': current_flight_amount,
            'total_amount': current_taxi_amount + current_hotel_amount + current_train_amount + current_flight_amount,
            'taxi_orders': current_taxi_orders,
            'hotel_orders': current_hotel_orders,
            'train_tickets': current_train_tickets,
            'flight_tickets': current_flight_tickets,
            'train_groups': current_train_groups,
            'taxi_warnings': current_taxi_warnings,
            'hotel_warnings': current_hotel_warnings
        }
        
        total_amount = all_classification_info['total_amount']
        
        # 🎉 彩蛋：更新全局统计数据（包括新处理和重用的订单）
        total_itineraries = len(all_results)  # 所有订单数量
        save_global_stats(total_itineraries, total_amount)
        logger.info(f"🎉 全局统计已更新！累计行程单数: {total_itineraries}")
        
        # 返回处理结果
        logger.info(f"文件处理完成，成功处理 {len(all_results)} 个订单，其中新处理 {len(new_results)} 个")
        logger.info(
            f"📊 分类统计: 网约车 {all_classification_info['taxi_amount']:.2f}元, "
            f"酒店 {all_classification_info['hotel_amount']:.2f}元, "
            f"火车票 {all_classification_info['train_tickets']} 张({all_classification_info['train_groups']} 组), "
            f"火车金额 {all_classification_info['train_amount']:.2f}元, "
            f"机票 {all_classification_info['flight_tickets']} 张, "
            f"机票金额 {all_classification_info['flight_amount']:.2f}元"
        )
        
        # 计算本次处理的金额（只计算新处理的订单，不包括重用的）
        # 从 new_results 中计算金额，而不是从 processed_files
        current_session_taxi_amount = 0
        current_session_hotel_amount = 0
        current_session_train_amount = 0
        current_session_flight_amount = 0
        
        # 方法1：从 new_results 直接计算（最准确）
        for result in new_results:
            amount = result.get('amount', 0)
            order_id = result.get('order_id', '')
            # 判断是网约车还是酒店（根据order_id前缀或文件类型）
            if result.get('has_flight_ticket'):
                current_session_flight_amount += result.get('flight_amount', amount)
                current_session_train_amount += result.get('train_amount', 0)
            elif result.get('is_train_merged_entry') or result.get('has_train_ticket'):
                current_session_train_amount += result.get('train_amount', amount)
            elif order_id.startswith('hotel_'):
                current_session_hotel_amount += amount
            else:
                current_session_taxi_amount += amount
        
        # 方法2：如果方法1没有金额，尝试从 processed_files 的 classification_info 计算
        # 但只计算新处理的文件，不包括重用的文件
        if current_session_taxi_amount == 0 and current_session_hotel_amount == 0 and current_session_train_amount == 0:
            for file_result in processed_files:
                if 'classification_info' in file_result:
                    info = file_result['classification_info']
                    current_session_taxi_amount += info.get('taxi_amount', 0)
                    current_session_hotel_amount += info.get('hotel_amount', 0)
                    current_session_train_amount += info.get('train_amount', 0)
                    current_session_flight_amount += info.get('flight_amount', 0)
        
        current_session_total = current_session_taxi_amount + current_session_hotel_amount + current_session_train_amount + current_session_flight_amount
        
        logger.info(
            f"📊 本次处理金额计算: 新订单数={len(new_results)}, "
            f"网约车={current_session_taxi_amount:.2f}元, "
            f"酒店={current_session_hotel_amount:.2f}元, "
            f"火车={current_session_train_amount:.2f}元, "
            f"机票={current_session_flight_amount:.2f}元, "
            f"总计={current_session_total:.2f}元"
        )
        
        # 将处理结果增量保存到session中（用于会话内记录与查看）
        session_existing_results = session.get('processed_files', [])
        merged_results_map = {}

        def _result_dedup_key(item):
            """构建稳定去重键，避免火车票增量上传时重复计数。"""
            if item.get('is_train_merged_entry'):
                return 'train_merged_all'
            if item.get('has_train_ticket') or item.get('has_flight_ticket') or str(item.get('combined_type', '')).startswith(('train_', 'flight_', 'ticket_')):
                order_id = item.get('order_id', '')
                pages = item.get('train_ticket_pages') or []
                page_sig = ','.join(str(p) for p in pages) if pages else 'p1'
                return f"ticket::{order_id}::{page_sig}"
            order_id = item.get('order_id')
            if order_id:
                return f"order::{order_id}"
            return item.get('output_file') or str(uuid.uuid4())

        for item in session_existing_results:
            merged_results_map[_result_dedup_key(item)] = item
        for item in all_results:
            merged_results_map[_result_dedup_key(item)] = item

        # 移除旧的火车票整合条目（上传阶段不自动重建，避免单文件上传被历史状态污染）
        merged_session_results = [
            item for item in merged_results_map.values()
            if not item.get('is_train_merged_entry')
        ]

        session['processed_files'] = merged_session_results
        session.modified = True
        logger.info(f"已将处理结果增量保存到session中，当前累计 {len(session['processed_files'])} 个")
        
        return jsonify({
            'success': True,
            'message': f'成功处理 {len(all_results)} 个订单',
            'results': all_results,
            'processed_files': len(processed_files),
            'reused_files': len(reused_files),
            'new_results_count': len(new_results),
            'total_amount': total_amount,
            'xml_missing_warnings': all_xml_warnings,  # 添加XML缺失警告
            'classification_info': all_classification_info,  # 添加分类统计信息
            'file_details': {
                'processed': processed_files,
                'reused': reused_files
            },
            # 本次处理统计
            'current_session': {
                'taxi_amount': current_session_taxi_amount,
                'hotel_amount': current_session_hotel_amount,
                'train_amount': current_session_train_amount,
                'flight_amount': current_session_flight_amount,
                'total_amount': current_session_total,
                'orders': len(new_results)
            }
        })
        
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'处理文件时出错: {str(e)}'}), 500

@main_bp.route('/api/upload-raw', methods=['POST'])
def upload_raw_file():
    """处理原始打印文件上传，支持ZIP文件自动解压"""
    logger = current_app.logger
    logger.info("收到原始打印文件上传请求")
    
    # 检查是否有文件
    if 'files' not in request.files:
        logger.warning("上传请求中没有文件")
        return jsonify({'error': '没有文件'}), 400
    
    files = request.files.getlist('files')
    
    # 检查是否有文件被选择
    if len(files) == 0 or files[0].filename == '':
        logger.warning("上传的文件名为空")
        return jsonify({'error': '没有选择文件'}), 400
    
    try:
        # 生成唯一的临时目录
        session_id = str(uuid.uuid4())
        logger.info(f"创建原始打印会话: {session_id}")
        
        temp_folder = os.path.join(current_app.config['TEMP_FOLDER'], f'raw_{session_id}')
        os.makedirs(temp_folder, exist_ok=True)
        
        uploaded_files = []
        extracted_files = []
        
        for file in files:
            # 保存文件
            original_filename = file.filename
            filename = secure_filename(file.filename)
            file_path = os.path.join(temp_folder, filename)
            file.save(file_path)
            logger.info(f"原始打印文件已保存到: {file_path}")
            logger.info(f"原始文件名: {original_filename}, 安全文件名: {filename}")
            
            # 检查是否为ZIP文件（使用原始文件名检查，因为secure_filename可能移除扩展名）
            if original_filename.lower().endswith('.zip') or filename.lower().endswith('.zip'):
                logger.info(f"发现ZIP文件: {filename}，开始解压")
                try:
                    # 为ZIP文件创建解压目录
                    extract_dir = os.path.join(temp_folder, f'extracted_{filename[:-4]}')
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    # 使用专门的ZIP解压函数
                    from app.services.file_service import extract_zip_for_raw_print
                    extracted_file_list = extract_zip_for_raw_print(file_path, extract_dir)
                    
                    # 将解压后的文件添加到结果中
                    extracted_files.extend(extracted_file_list)
                    logger.info(f"ZIP文件 {filename} 解压完成，解压出 {len(extracted_file_list)} 个文件")
                    
                except Exception as e:
                    logger.error(f"解压ZIP文件 {filename} 时出错: {str(e)}")
                    # 解压失败时，仍然将ZIP文件本身作为可打印文件
                    uploaded_files.append({
                        'name': filename,
                        'filename': filename,
                        'file_path': file_path,
                        'size': os.path.getsize(file_path),
                        'type': 'archive',
                        'file_type': 'archive',
                        'extension': '.zip',
                        'is_printable': True
                    })
                    logger.info(f"ZIP文件解压失败，将ZIP文件本身添加到可打印文件列表")
            else:
                # 普通文件直接添加
                uploaded_files.append({
                    'name': original_filename,  # 使用原始文件名显示
                    'filename': filename,       # 使用安全文件名存储
                    'file_path': file_path,
                    'size': os.path.getsize(file_path),
                    'type': get_file_type(filename),
                    'file_type': get_file_type(filename),
                    'extension': os.path.splitext(filename)[1].lower(),
                    'is_printable': True
                })
        
        # 合并所有文件（解压后的文件优先）
        all_files = extracted_files + uploaded_files
        
        logger.info(f"原始打印文件处理完成，共 {len(all_files)} 个文件（包含解压后的文件）")
        logger.info(f"解压后的文件数量: {len(extracted_files)}")
        logger.info(f"普通文件数量: {len(uploaded_files)}")
        
        # 如果有解压后的文件，返回解压后的文件列表
        if extracted_files:
            logger.info(f"返回解压后的文件列表，共 {len(extracted_files)} 个文件")
            return jsonify({
                'success': True,
                'message': f'成功上传并解压 {len(files)} 个文件，解压出 {len(extracted_files)} 个文件',
                'extracted_files': extracted_files,
                'original_files': uploaded_files,
                'total_files': len(all_files)
            })
        else:
            # 没有ZIP文件，返回普通文件列表
            logger.info(f"没有解压后的文件，返回普通文件列表，共 {len(uploaded_files)} 个文件")
            return jsonify({
                'success': True,
                'message': f'成功上传 {len(uploaded_files)} 个文件',
                'files': uploaded_files,
                'total_files': len(uploaded_files)
            })
        
    except Exception as e:
        logger.error(f"上传原始打印文件时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'上传文件时出错: {str(e)}'}), 500

def get_file_type(filename):
    """根据文件名获取文件类型"""
    if not filename:
        return 'unknown'
    
    ext = os.path.splitext(filename)[1].lower()
    
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

@main_bp.route('/api/print-raw', methods=['POST'])
def print_raw_file():
    """原始打印文件。直接通过 CUPS 提交，不再依赖独立打印服务进程。"""
    logger = current_app.logger
    logger.info("收到原始打印请求")
    
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'success': False, 'message': '缺少文件名参数'}), 400
        
        filename = data.get('filename')
        action = data.get('action', 'print')
        
        logger.info(f"原始打印文件: {filename}, 操作: {action}")
        
        # 在临时目录中查找文件
        temp_folder = current_app.config['TEMP_FOLDER']
        file_found = False
        file_path = None
        
        # 递归搜索临时目录中的文件
        for root, dirs, files in os.walk(temp_folder):
            if filename in files:
                file_path = os.path.join(root, filename)
                file_found = True
                break
        
        if not file_found or not os.path.exists(file_path):
            logger.error(f"文件未找到: {filename}")
            return jsonify({'success': False, 'message': f'文件 {filename} 未找到，可能已被清理或移动'}), 404
        
        logger.info(f"找到文件: {file_path}")
        
        printer_name = (data.get('printer_name') or '').strip() or None
        copies = int(data.get('copies', 1))
        tray = (data.get('tray') or '').strip() or None

        print_path = prepare_raw_pdf_for_a4_print(file_path)
        logger.info(f"开始提交原始打印: {print_path}, printer={printer_name}, copies={copies}, tray={tray}")
        print_result = print_pdf(
            print_path,
            printer_name=printer_name,
            copies=copies,
            media_source=tray,
        )
        status_code = 200 if print_result.get('success') else 500
        return jsonify({
            'success': print_result.get('success', False),
            'message': print_result.get('message', '打印失败'),
            'printer': print_result.get('printer', printer_name or '未知打印机'),
            'job_id': print_result.get('job_id', '')
        }), status_code
            
    except Exception as e:
        logger.error(f"原始打印文件时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'打印文件时出错: {str(e)}'}), 500


@main_bp.route('/api/print-raw-batch', methods=['POST'])
def print_raw_files_batch():
    """批量原始打印文件 - 支持一次打印多个PDF文件"""
    logger = current_app.logger
    logger.info("收到批量原始打印请求")
    
    try:
        data = request.get_json()
        if not data or 'filenames' not in data:
            return jsonify({'success': False, 'message': '缺少文件名列表参数'}), 400
        
        filenames = data.get('filenames', [])
        if not isinstance(filenames, list) or len(filenames) == 0:
            return jsonify({'success': False, 'message': '文件名列表为空或格式错误'}), 400
        
        logger.info(f"批量打印请求: {len(filenames)} 个文件")
        logger.info(f"文件列表: {filenames}")
        
        printer_name = (data.get('printer_name') or '').strip() or None
        copies = int(data.get('copies', 1))
        tray = (data.get('tray') or '').strip() or None
        
        # 在临时目录中查找所有文件
        temp_folder = current_app.config['TEMP_FOLDER']
        
        # 批量处理结果
        print_results = []
        success_count = 0
        failed_count = 0
        
        for filename in filenames:
            file_found = False
            file_path = None
            
            # 递归搜索临时目录中的文件
            for root, dirs, files in os.walk(temp_folder):
                if filename in files:
                    file_path = os.path.join(root, filename)
                    file_found = True
                    break
            
            if not file_found or not os.path.exists(file_path):
                logger.warning(f"文件未找到: {filename}")
                print_results.append({
                    'filename': filename,
                    'success': False,
                    'message': f'文件 {filename} 未找到，可能已被清理或移动',
                    'printer': printer_name,
                    'job_id': None
                })
                failed_count += 1
                continue
            
            logger.info(f"找到文件: {file_path}，开始打印")
            
            try:
                print_path = prepare_raw_pdf_for_a4_print(file_path)
                print_result = print_pdf(
                    print_path,
                    printer_name=printer_name,
                    copies=copies,
                    media_source=tray,
                )
                if print_result.get('success'):
                    logger.info(f"文件 {filename} 打印任务提交成功")
                    print_results.append({
                        'filename': filename,
                        'success': True,
                        'message': print_result.get('message', f'文件 {filename} 已发送至打印机'),
                        'printer': print_result.get('printer', printer_name),
                        'job_id': print_result.get('job_id', '')
                    })
                    success_count += 1
                else:
                    logger.error(f"文件 {filename} 打印失败: {print_result.get('message')}")
                    print_results.append({
                        'filename': filename,
                        'success': False,
                        'message': print_result.get('message', f'文件 {filename} 打印失败'),
                        'printer': print_result.get('printer', printer_name),
                        'job_id': print_result.get('job_id', None)
                    })
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"打印文件 {filename} 时出错: {str(e)}")
                print_results.append({
                    'filename': filename,
                    'success': False,
                    'message': f'打印文件 {filename} 时出错: {str(e)}',
                    'printer': printer_name,
                    'job_id': None
                })
                failed_count += 1
        
        # 返回批量打印结果
        logger.info(f"批量打印完成: 成功 {success_count}/{len(filenames)}, 失败 {failed_count}/{len(filenames)}")
        
        return jsonify({
            'success': True,
            'message': f'批量打印完成: {success_count} 个成功, {failed_count} 个失败',
            'total': len(filenames),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': print_results
        })
        
    except Exception as e:
        logger.error(f"批量原始打印文件时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'批量打印文件时出错: {str(e)}'}), 500


@main_bp.route('/api/get-raw-file', methods=['POST'])
def get_raw_file():
    """获取原始打印文件路径用于预览"""
    logger = current_app.logger
    logger.info("收到获取原始打印文件请求")
    
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'success': False, 'message': '缺少文件名参数'}), 400
        
        filename = data.get('filename')
        logger.info(f"请求预览文件: {filename}")
        
        # 在临时目录中查找文件
        temp_folder = current_app.config['TEMP_FOLDER']
        file_found = False
        file_path = None
        
        # 递归搜索临时目录中的文件
        for root, dirs, files in os.walk(temp_folder):
            if filename in files:
                file_path = os.path.join(root, filename)
                file_found = True
                break
        
        if file_found and os.path.exists(file_path):
            logger.info(f"找到文件: {file_path}")
            
            # 生成一个安全的访问令牌
            import hashlib
            import time
            token = hashlib.md5(f"{filename}_{time.time()}".encode()).hexdigest()
            
            # 将文件路径和令牌存储到会话中（临时解决方案）
            # 在实际生产环境中，应该使用Redis等缓存系统
            if not hasattr(current_app, 'file_tokens'):
                current_app.file_tokens = {}
            current_app.file_tokens[token] = file_path
            
            # 返回文件访问URL
            preview_url = f"/api/preview-file/{token}"
            
            return jsonify({
                'success': True,
                'preview_url': preview_url,
                'filename': filename,
                'size': os.path.getsize(file_path),
                'message': f'文件 {filename} 预览链接生成成功'
            })
        else:
            logger.warning(f"文件未找到: {filename}")
            return jsonify({
                'success': False,
                'message': f'文件 {filename} 未找到，可能已被清理或移动'
            }), 404
        
    except Exception as e:
        logger.error(f"获取原始打印文件时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'获取文件时出错: {str(e)}'}), 500

@main_bp.route('/api/preview-smart-processed', methods=['POST'])
def preview_smart_processed():
    """预览智能处理后的PDF文件"""
    logger = current_app.logger
    logger.info("收到智能处理文件预览请求")
    
    try:
        data = request.get_json()
        if not data or 'order_data' not in data:
            return jsonify({'success': False, 'message': '缺少订单数据参数'}), 400
        
        order_data = data['order_data']
        logger.info(f"预览订单: {order_data}")
        
        # 智能处理阶段已经完成了拼接，这里直接预览生成的文件
        try:
            logger.info(f"开始智能拼接预览: {order_data}")
            
            # 根据订单数据找到对应的文件
            # 智能处理阶段已经完成了拼接，这里直接预览生成的文件
            output_file = order_data.get('output_file')
            if not output_file:
                return jsonify({
                    'success': False,
                    'message': '缺少输出文件信息'
                }), 400
            
            # 构建完整的文件路径
            output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_file)
            if not os.path.exists(output_path):
                return jsonify({
                    'success': False,
                    'message': f'输出文件不存在: {output_path}'
                }), 404
            
            # 直接返回输出文件的预览链接
            # 这个文件已经是智能拼接后的结果，不需要重新拼接
            preview_url = f"/output/{output_file}"
            
            logger.info(f"智能拼接预览成功: {preview_url}")
            return jsonify({
                'success': True,
                'preview_url': preview_url,
                'message': '智能拼接预览成功（文件已在处理阶段完成拼接）'
            })
            
        except Exception as e:
            logger.error(f"智能拼接预览失败: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'智能拼接预览失败: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"智能处理文件预览时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'预览文件时出错: {str(e)}'}), 500

@main_bp.route('/api/preview-file/<token>')
def preview_file(token):
    """通过令牌预览文件"""
    logger = current_app.logger
    logger.info(f"收到文件预览请求，令牌: {token}")
    
    try:
        # 从令牌中获取文件路径
        if not hasattr(current_app, 'file_tokens') or token not in current_app.file_tokens:
            logger.warning(f"无效的预览令牌: {token}")
            return jsonify({'error': '无效的预览令牌'}), 404
        
        file_path = current_app.file_tokens[token]
        
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return jsonify({'error': '文件不存在'}), 404
        
        # 获取文件信息
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # 检查文件类型
        file_ext = os.path.splitext(filename)[1].lower()
        
        # 对于图片和PDF文件，直接返回文件内容
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pdf']:
            logger.info(f"直接预览文件: {filename}")
            return send_from_directory(os.path.dirname(file_path), filename)
        
        # 对于其他文件类型，返回下载链接
        else:
            logger.info(f"提供文件下载: {filename}")
            return send_from_directory(
                os.path.dirname(file_path), 
                filename, 
                as_attachment=True,
                download_name=filename
            )
            
    except Exception as e:
        logger.error(f"预览文件时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'预览文件时出错: {str(e)}'}), 500

@main_bp.route('/api/print/<filename>', methods=['POST'])
def print_file(filename):
    """打印指定的PDF文件"""
    logger = current_app.logger
    logger.info(f"收到打印请求: {filename}")
    
    try:
        file_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return jsonify({'success': False, 'message': '文件不存在', 'error': '文件不存在'}), 404
        
        print_result = print_pdf(file_path)
        logger.info(f"文件已发送至打印机: {file_path}")
        
        # 返回打印结果的详细信息
        return jsonify({
            'success': print_result.get('success', False),
            'message': f"文件已发送至打印机: {print_result.get('message', '未知打印机')}",
            'printer': print_result.get('printer', '未知打印机'),
            'job_id': print_result.get('job_id', ''),
            'debug': print_result.get('debug', False)
        })
    except Exception as e:
        logger.error(f"打印文件时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'打印文件时出错: {str(e)}', 'error': str(e)}), 500


@main_bp.route('/api/reprint/<file_hash>', methods=['POST'])
def reprint_file(file_hash):
    """重新打印指定哈希值的文件"""
    logger = current_app.logger
    logger.info(f"收到重新打印请求: {file_hash}")
    
    try:
        # 获取文件信息
        existing_file = check_file_exists(file_hash)
        if not existing_file:
            return jsonify({'success': False, 'message': '文件不存在', 'error': '文件不存在'}), 404
        
        # 获取文件结果
        results = existing_file.get('results', [])
        logger.info(f"文件 {file_hash} 包含 {len(results)} 个结果")
        
        if not results:
            return jsonify({'success': False, 'message': '没有可打印的文件', 'error': '没有可打印的文件'}), 400
        
        # 打印所有PDF文件
        print_results = []
        success_count = 0
        
        for result in results:
            logger.info(f"处理结果: {result}")
            if 'output_file' in result:
                output_filename = result['output_file']
                file_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
                logger.info(f"找到输出文件: {output_filename}, 路径: {file_path}")
                
                if os.path.exists(file_path):
                    print_result = print_pdf(file_path)
                    print_results.append({
                        'filename': output_filename,
                        'success': print_result.get('success', False),
                        'message': print_result.get('message', '打印失败'),
                        'printer': print_result.get('printer', '未知打印机'),
                        'job_id': print_result.get('job_id', '')
                    })
                    
                    if print_result.get('success', False):
                        success_count += 1
                else:
                    print_results.append({
                        'filename': output_filename,
                        'success': False,
                        'message': '文件不存在',
                        'printer': '未知打印机',
                        'job_id': ''
                    })
        
        # 更新打印状态
        if success_count > 0:
            print_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            update_file_print_status(file_hash, 'printed', print_time)
        
        logger.info(f"重新打印完成，成功打印 {success_count}/{len(results)} 个文件")
        
        return jsonify({
            'success': success_count > 0,
            'message': f'重新打印完成，成功打印 {success_count}/{len(results)} 个文件',
            'print_results': print_results,
            'total_files': len(results),
            'success_count': success_count
        })
        
    except Exception as e:
        logger.error(f"重新打印文件时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'重新打印文件时出错: {str(e)}', 'error': str(e)}), 500

@main_bp.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取所有用户的统计数据"""
    logger = current_app.logger
    logger.info("收到获取统计数据请求")
    
    try:
        stats = get_all_user_stats()
        logger.info(f"返回统计数据，用户数: {len(stats)}")
        return jsonify(stats)
    except Exception as e:
        logger.error(f"获取统计数据时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'获取统计数据时出错: {str(e)}'}), 500

@main_bp.route('/api/global-stats', methods=['GET'])
def get_global_statistics():
    """🎉 获取全局统计数据（彩蛋功能）"""
    logger = current_app.logger
    logger.info("收到获取全局统计数据请求")
    
    try:
        from app.services.user_service import get_global_stats
        global_stats = get_global_stats()
        logger.info(f"🎉 返回全局统计数据，总行程单数: {global_stats.get('total_itineraries', 0)}")
        return jsonify(global_stats)
    except Exception as e:
        logger.error(f"获取全局统计数据时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'获取全局统计数据时出错: {str(e)}'}), 500

@main_bp.route('/output/<filename>')
def get_output_file(filename):
    """获取生成的PDF文件"""
    logger = current_app.logger
    logger.debug(f"请求获取输出文件: {filename}")
    return send_from_directory(current_app.config['OUTPUT_FOLDER'], filename)


@main_bp.route('/api/download-collection', methods=['POST'])
def download_collection():
    """创建并下载PDF合集"""
    logger = current_app.logger
    logger.info("收到下载合集请求")
    
    try:
        # 获取请求数据
        data = request.get_json()
        processed_files = data.get('processed_files', [])
        collection_name = data.get('collection_name', '报销单据合集')
        
        if not processed_files:
            return jsonify({'success': False, 'message': '没有可下载的文件'}), 400
        
        logger.info(f"开始创建合集，文件数量: {len(processed_files)}")
        
        # 调用PDF服务创建合集
        from app.services.pdf_service import create_download_collection
        result = create_download_collection(processed_files, collection_name)
        
        if result['success']:
            # 生成下载令牌
            import uuid
            token = str(uuid.uuid4())
            
            # 存储文件路径到令牌
            if not hasattr(current_app, 'file_tokens'):
                current_app.file_tokens = {}
            current_app.file_tokens[token] = result['file_path']
            
            logger.info(f"✅ 合集创建成功: {result['filename']}")
            return jsonify({
                'success': True,
                'filename': result['filename'],
                'download_url': f'/api/download-file/{token}',
                'file_count': result['file_count']
            })
        else:
            logger.error(f"❌ 合集创建失败: {result['message']}")
            return jsonify({
                'success': False,
                'message': result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"创建下载合集时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'创建合集时出错: {str(e)}'}), 500


@main_bp.route('/api/print-merged', methods=['POST'])
def print_merged_collection():
    """将多个处理结果先合并为单个PDF，再一次性提交打印。"""
    logger = current_app.logger
    logger.info("收到整合打印请求")

    try:
        data = request.get_json() or {}
        processed_files = data.get('processed_files', [])
        only_train = bool(data.get('only_train', False))
        collection_name = data.get('collection_name', '整合打印合集')

        if not processed_files:
            return jsonify({'success': False, 'message': '没有可打印的文件'}), 400

        selected_files = [f for f in processed_files if not f.get('is_train_merged_entry')]
        if only_train:
            selected_files = [
                f for f in selected_files
                if (
                    f.get('has_train_ticket')
                    or f.get('has_flight_ticket')
                    or f.get('has_transport_ticket')
                    or str(f.get('combined_type', '')).startswith(('train_', 'flight_', 'ticket_'))
                )
            ]
            logger.info(f"整合打印(transport-only)筛选结果: {len(selected_files)}/{len(processed_files)}")

        if not selected_files:
            return jsonify({'success': False, 'message': '未找到可整合的火车票/机票文件'}), 400

        # 优先复用“按火车票布局规则重排”的整合条目，确保跨ZIP不是简单拼接
        from app.services.pdf_service import create_train_merged_entry, create_download_collection
        train_merge = create_train_merged_entry(selected_files)
        if train_merge.get('success'):
            merged_path = train_merge.get('file_path')
            merged_filename = train_merge.get('result', {}).get('output_file', '')
        else:
            # 非火车场景回退到普通合集
            merge_result = create_download_collection(selected_files, collection_name)
            if not merge_result.get('success'):
                return jsonify({
                    'success': False,
                    'message': merge_result.get('message', '整合文件创建失败')
                }), 500
            merged_path = merge_result['file_path']
            merged_filename = merge_result.get('filename', '')

        if not merged_path:
            return jsonify({
                'success': False,
                'message': train_merge.get('message', '整合文件创建失败')
            }), 500

        print_result = print_pdf(merged_path)
        ok = bool(print_result.get('success'))

        logger.info(
            f"整合打印完成: success={ok}, merged={merged_filename}, "
            f"files={len(selected_files)}, printer={print_result.get('printer', '')}"
        )
        return jsonify({
            'success': ok,
            'message': print_result.get('message', '整合打印完成'),
            'printer': print_result.get('printer', '未知打印机'),
            'job_id': print_result.get('job_id', ''),
            'merged_file': merged_filename,
            'file_count': len(selected_files),
            'train_only': only_train,
        }), (200 if ok else 500)

    except Exception as e:
        logger.error(f"整合打印时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'整合打印时出错: {str(e)}'}), 500


@main_bp.route('/api/train-merged-entry', methods=['POST'])
def train_merged_entry():
    """生成/刷新火车票整合条目（用于前端结果区预览与单条打印）。"""
    logger = current_app.logger
    logger.info("收到火车票整合条目生成请求")

    try:
        data = request.get_json() or {}
        request_files = data.get('processed_files', [])

        # 严格基于前端传入的当前列表做整合，避免历史session污染当前批次
        source_files = [f for f in request_files if not f.get('is_train_merged_entry')]
        if not source_files:
            return jsonify({'success': False, 'message': '没有可处理的订单结果'}), 400

        from app.services.pdf_service import create_train_merged_entry
        merge_result = create_train_merged_entry(source_files)
        if not merge_result.get('success'):
            return jsonify({
                'success': False,
                'message': merge_result.get('message', '火车票整合条目生成失败')
            }), 400

        merged_result = merge_result.get('result', {})
        logger.info(
            f"火车票整合条目生成成功: output={merged_result.get('output_file')}, "
            f"tickets={merged_result.get('train_ticket_count')}, pages={merged_result.get('page_count')}, "
            f"order={merged_result.get('train_merge_order')}"
        )
        return jsonify({
            'success': True,
            'message': '火车票整合条目生成成功',
            'result': merged_result,
        })
    except Exception as e:
        logger.error(f"生成火车票整合条目时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'生成火车票整合条目时出错: {str(e)}'}), 500


@main_bp.route('/api/download-file/<token>')
def download_file(token):
    """通过令牌下载文件"""
    logger = current_app.logger
    logger.info(f"收到文件下载请求，令牌: {token}")
    
    try:
        # 从令牌中获取文件路径
        if not hasattr(current_app, 'file_tokens') or token not in current_app.file_tokens:
            logger.warning(f"无效的下载令牌: {token}")
            return jsonify({'error': '无效的下载令牌'}), 404
        
        file_path = current_app.file_tokens[token]
        
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return jsonify({'error': '文件不存在'}), 404
        
        # 获取文件名
        filename = os.path.basename(file_path)
        
        # 返回文件下载
        logger.info(f"开始下载文件: {filename}")
        return send_from_directory(
            os.path.dirname(file_path), 
            filename, 
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"下载文件时出错: {str(e)}", exc_info=True)
        return jsonify({'error': f'下载文件时出错: {str(e)}'}), 500


@main_bp.route('/api/view-trips', methods=['POST'])
def view_trips():
    """查看行程记录"""
    logger = current_app.logger
    logger.info("收到查看行程记录请求")
    
    try:
        # 获取请求数据
        data = request.get_json()
        processed_files = data.get('processed_files', [])
        
        if not processed_files:
            return jsonify({'success': False, 'message': '没有可查看的文件'}), 400
        
        # 检查是否有包含行程单的文件
        has_itinerary = any(file_info.get('has_itinerary', False) for file_info in processed_files)
        if not has_itinerary:
            return jsonify({'success': False, 'message': '没有包含行程单的文件'}), 400
        
        logger.info(f"开始生成行程记录，文件数量: {len(processed_files)}")
        
        # 调用PDF服务生成行程记录
        from app.services.pdf_service import generate_trip_records
        trip_records = generate_trip_records(processed_files)
        
        # 更新session中的processed_files，确保缓存被保存
        if 'processed_files' in session:
            session_processed_files = session['processed_files']
            logger.info(f"Session中有 {len(session_processed_files)} 个文件")
            
            # 更新session中的文件信息，包含新的缓存
            updated_count = 0
            for session_file in session_processed_files:
                for request_file in processed_files:
                    if (session_file.get('order_id') == request_file.get('order_id') and 
                        session_file.get('output_file') == request_file.get('output_file')):
                        # 更新缓存信息
                        if 'cached_trip_records' in request_file:
                            session_file['cached_trip_records'] = request_file['cached_trip_records']
                            updated_count += 1
                            logger.info(f"已更新文件 {request_file.get('output_file')} 的缓存到session")
                        break
            session['processed_files'] = session_processed_files
            session.modified = True
            logger.info(f"已更新session中的行程记录缓存，共更新 {updated_count} 个文件")
        else:
            logger.warning("Session中没有processed_files，无法更新缓存")
        
        logger.info("✅ 行程记录生成成功")
        return jsonify({
            'success': True,
            'trip_records': trip_records,
            'file_count': len(processed_files)
        })
        
    except Exception as e:
        logger.error(f"生成行程记录时出错: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'生成行程记录时出错: {str(e)}'}), 500 