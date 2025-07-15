import os
import re
import uuid
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader, PdfWriter
from flask import current_app
from app.services.file_service import get_file_paths, group_files_by_type

def extract_amount_from_xml(xml_path):
    """从XML文件中提取订单金额"""
    logger = current_app.logger
    try:
        logger.debug(f"正在从XML文件提取金额: {xml_path}")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 尝试查找金额信息 (根据实际XML结构调整)
        # 这里假设XML中有一个标签包含金额信息
        amount_elem = root.find(".//Amount") or root.find(".//TotalAmount") or root.find(".//Price")
        if amount_elem is not None and amount_elem.text:
            try:
                amount = float(amount_elem.text)
                logger.debug(f"从XML标签中提取到金额: {amount}")
                return amount
            except ValueError:
                logger.warning(f"无法将XML标签值转换为浮点数: {amount_elem.text}")
                pass
        
        # 如果没有找到特定标签，尝试在整个XML文本中搜索金额模式
        xml_text = ET.tostring(root, encoding='utf-8').decode('utf-8')
        amount_matches = re.findall(r'金额[：:]\s*(\d+\.\d+)', xml_text)
        if amount_matches:
            amount = float(amount_matches[0])
            logger.debug(f"从XML文本中提取到金额: {amount}")
            return amount
        
        # 如果以上都失败，返回0
        logger.warning(f"无法从XML文件中提取金额: {xml_path}")
        return 0
    except Exception as e:
        logger.error(f"解析XML文件出错: {str(e)}")
        return 0

def identify_pdf_type(pdf_path):
    """识别PDF文件类型（行程单或发票）"""
    logger = current_app.logger
    try:
        filename = os.path.basename(pdf_path).lower()
        logger.debug(f"正在识别PDF类型: {pdf_path}")
        
        # 通过文件名判断
        if '发票' in filename or 'invoice' in filename or 'receipt' in filename:
            logger.debug(f"通过文件名识别为发票: {pdf_path}")
            return 'invoice'
        elif '行程' in filename or 'itinerary' in filename or 'trip' in filename:
            logger.debug(f"通过文件名识别为行程单: {pdf_path}")
            return 'itinerary'
        
        # 通过文件内容判断（简单版）
        reader = PdfReader(pdf_path)
        if len(reader.pages) > 0:
            text = reader.pages[0].extract_text().lower()
            if '发票' in text or 'invoice' in text or 'receipt' in text:
                logger.debug(f"通过内容识别为发票: {pdf_path}")
                return 'invoice'
            elif '行程' in text or 'itinerary' in text or 'trip' in text:
                logger.debug(f"通过内容识别为行程单: {pdf_path}")
                return 'itinerary'
        
        # 默认返回未知类型
        logger.warning(f"无法识别PDF类型: {pdf_path}")
        return 'unknown'
    except Exception as e:
        logger.error(f"识别PDF类型出错: {str(e)}")
        return 'unknown'

def extract_order_id(file_path):
    """从文件名或内容中提取订单ID"""
    logger = current_app.logger
    try:
        logger.debug(f"正在提取订单ID: {file_path}")
        # 从文件名中提取
        filename = os.path.basename(file_path)
        # 假设订单ID是文件名中的数字部分
        order_id_match = re.search(r'(\d{6,})', filename)
        if order_id_match:
            order_id = order_id_match.group(1)
            logger.debug(f"从文件名中提取到订单ID: {order_id}")
            return order_id
        
        # 如果是PDF，尝试从内容中提取
        if file_path.lower().endswith('.pdf'):
            reader = PdfReader(file_path)
            if len(reader.pages) > 0:
                text = reader.pages[0].extract_text()
                # 尝试查找订单号模式
                order_id_match = re.search(r'订单[号#]?[：:]?\s*(\d{6,})', text)
                if order_id_match:
                    order_id = order_id_match.group(1)
                    logger.debug(f"从PDF内容中提取到订单ID: {order_id}")
                    return order_id
        
        # 如果是XML，尝试从内容中提取
        if file_path.lower().endswith('.xml'):
            tree = ET.parse(file_path)
            root = tree.getroot()
            # 尝试查找订单号元素
            order_elem = root.find(".//OrderID") or root.find(".//OrderNumber")
            if order_elem is not None and order_elem.text:
                order_id = order_elem.text
                logger.debug(f"从XML内容中提取到订单ID: {order_id}")
                return order_id
        
        # 如果无法提取，使用文件名的ASCII部分作为标识
        # 过滤掉非ASCII字符，避免乱码
        ascii_filename = ''.join(c for c in os.path.splitext(filename)[0] if ord(c) < 128)
        if not ascii_filename:
            ascii_filename = str(uuid.uuid4())[:8]
        
        logger.warning(f"无法提取订单ID，使用文件名作为标识: {ascii_filename}")
        return ascii_filename
    except Exception as e:
        logger.error(f"提取订单ID出错: {str(e)}")
        random_id = str(uuid.uuid4())[:8]
        logger.debug(f"使用随机ID作为后备: {random_id}")
        return random_id  # 生成随机ID作为后备

def match_files_by_order(pdf_files, xml_files):
    """将PDF和XML文件按订单匹配"""
    logger = current_app.logger
    logger.info(f"开始匹配文件，PDF文件数: {len(pdf_files)}，XML文件数: {len(xml_files)}")
    
    orders = {}
    
    # 处理XML文件
    for xml_path in xml_files:
        order_id = extract_order_id(xml_path)
        amount = extract_amount_from_xml(xml_path)
        
        if order_id not in orders:
            orders[order_id] = {'xml': xml_path, 'amount': amount, 'pdfs': {'invoice': None, 'itinerary': None}}
            logger.debug(f"创建新订单: {order_id}, 金额: {amount}")
        else:
            orders[order_id]['xml'] = xml_path
            orders[order_id]['amount'] = amount
            logger.debug(f"更新订单信息: {order_id}, 金额: {amount}")
    
    # 处理PDF文件
    for pdf_path in pdf_files:
        order_id = extract_order_id(pdf_path)
        pdf_type = identify_pdf_type(pdf_path)
        
        if pdf_type != 'unknown':
            if order_id not in orders:
                orders[order_id] = {'xml': None, 'amount': 0, 'pdfs': {'invoice': None, 'itinerary': None}}
                logger.debug(f"创建新订单(来自PDF): {order_id}")
            
            orders[order_id]['pdfs'][pdf_type] = pdf_path
            logger.debug(f"为订单 {order_id} 添加 {pdf_type} 类型的PDF: {pdf_path}")
    
    logger.info(f"文件匹配完成，共找到 {len(orders)} 个订单")
    return orders

def merge_pdfs(itinerary_path, invoice_path, output_path):
    """合并行程单和发票PDF"""
    logger = current_app.logger
    logger.info(f"开始合并PDF，行程单: {itinerary_path}, 发票: {invoice_path}")
    
    output = PdfWriter()
    
    # 添加行程单（在前）
    if itinerary_path:
        try:
            itinerary = PdfReader(itinerary_path)
            for page in itinerary.pages:
                output.add_page(page)
            logger.debug(f"已添加行程单，页数: {len(itinerary.pages)}")
        except Exception as e:
            logger.error(f"添加行程单时出错: {str(e)}")
    
    # 添加发票（在后）
    if invoice_path:
        try:
            invoice = PdfReader(invoice_path)
            for page in invoice.pages:
                output.add_page(page)
            logger.debug(f"已添加发票，页数: {len(invoice.pages)}")
        except Exception as e:
            logger.error(f"添加发票时出错: {str(e)}")
    
    # 保存合并后的PDF
    try:
        with open(output_path, "wb") as output_file:
            output.write(output_file)
        logger.info(f"PDF合并完成，输出文件: {output_path}")
    except Exception as e:
        logger.error(f"保存合并PDF时出错: {str(e)}")
        raise
    
    return output_path

def process_pdf_files(extract_dir):
    """处理解压后的PDF和XML文件"""
    logger = current_app.logger
    logger.info(f"开始处理解压后的文件: {extract_dir}")
    
    # 获取所有文件路径
    file_paths = get_file_paths(extract_dir)
    grouped_files = group_files_by_type(file_paths)
    
    # 按订单匹配文件
    orders = match_files_by_order(grouped_files['pdf'], grouped_files['xml'])
    
    results = []
    
    # 处理每个订单
    order_count = 0
    for order_id, order_data in orders.items():
        # 检查是否有足够的文件进行处理
        itinerary_path = order_data['pdfs']['itinerary']
        invoice_path = order_data['pdfs']['invoice']
        
        if not itinerary_path and not invoice_path:
            logger.warning(f"订单 {order_id} 没有PDF文件，跳过处理")
            continue
        
        # 使用简单的序号作为文件名前缀，避免使用中文文件名
        order_count += 1
        
        # 生成输出文件名 (使用序号和随机字符串，避免使用可能包含中文的order_id)
        output_filename = f"order_{order_count}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
        
        logger.info(f"处理订单 {order_id} (序号 {order_count})，输出文件: {output_filename}")
        
        # 合并PDF
        try:
            merge_pdfs(itinerary_path, invoice_path, output_path)
            
            # 添加处理结果
            results.append({
                'order_id': order_id,
                'amount': order_data['amount'],
                'output_file': output_filename,
                'has_itinerary': itinerary_path is not None,
                'has_invoice': invoice_path is not None
            })
            logger.info(f"订单 {order_id} 处理成功")
        except Exception as e:
            logger.error(f"处理订单 {order_id} 时出错: {str(e)}")
    
    logger.info(f"所有订单处理完成，成功处理 {len(results)} 个订单")
    return results 