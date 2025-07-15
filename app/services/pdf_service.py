import os
import re
import uuid
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader, PdfWriter
from flask import current_app
from app.services.file_service import get_file_paths, group_files_by_type

def extract_amount_from_xml(xml_path):
    """从XML文件中提取订单金额"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 尝试查找金额信息 (根据实际XML结构调整)
        # 这里假设XML中有一个标签包含金额信息
        amount_elem = root.find(".//Amount") or root.find(".//TotalAmount") or root.find(".//Price")
        if amount_elem is not None and amount_elem.text:
            try:
                return float(amount_elem.text)
            except ValueError:
                pass
        
        # 如果没有找到特定标签，尝试在整个XML文本中搜索金额模式
        xml_text = ET.tostring(root, encoding='utf-8').decode('utf-8')
        amount_matches = re.findall(r'金额[：:]\s*(\d+\.\d+)', xml_text)
        if amount_matches:
            return float(amount_matches[0])
        
        # 如果以上都失败，返回0
        return 0
    except Exception as e:
        print(f"解析XML文件出错: {str(e)}")
        return 0

def identify_pdf_type(pdf_path):
    """识别PDF文件类型（行程单或发票）"""
    try:
        filename = os.path.basename(pdf_path).lower()
        
        # 通过文件名判断
        if '发票' in filename or 'invoice' in filename or 'receipt' in filename:
            return 'invoice'
        elif '行程' in filename or 'itinerary' in filename or 'trip' in filename:
            return 'itinerary'
        
        # 通过文件内容判断（简单版）
        reader = PdfReader(pdf_path)
        if len(reader.pages) > 0:
            text = reader.pages[0].extract_text().lower()
            if '发票' in text or 'invoice' in text or 'receipt' in text:
                return 'invoice'
            elif '行程' in text or 'itinerary' in text or 'trip' in text:
                return 'itinerary'
        
        # 默认返回未知类型
        return 'unknown'
    except Exception as e:
        print(f"识别PDF类型出错: {str(e)}")
        return 'unknown'

def extract_order_id(file_path):
    """从文件名或内容中提取订单ID"""
    try:
        # 从文件名中提取
        filename = os.path.basename(file_path)
        # 假设订单ID是文件名中的数字部分
        order_id_match = re.search(r'(\d{6,})', filename)
        if order_id_match:
            return order_id_match.group(1)
        
        # 如果是PDF，尝试从内容中提取
        if file_path.lower().endswith('.pdf'):
            reader = PdfReader(file_path)
            if len(reader.pages) > 0:
                text = reader.pages[0].extract_text()
                # 尝试查找订单号模式
                order_id_match = re.search(r'订单[号#]?[：:]?\s*(\d{6,})', text)
                if order_id_match:
                    return order_id_match.group(1)
        
        # 如果是XML，尝试从内容中提取
        if file_path.lower().endswith('.xml'):
            tree = ET.parse(file_path)
            root = tree.getroot()
            # 尝试查找订单号元素
            order_elem = root.find(".//OrderID") or root.find(".//OrderNumber")
            if order_elem is not None and order_elem.text:
                return order_elem.text
        
        # 如果无法提取，返回文件名作为标识
        return os.path.splitext(filename)[0]
    except Exception as e:
        print(f"提取订单ID出错: {str(e)}")
        return str(uuid.uuid4())[:8]  # 生成随机ID作为后备

def match_files_by_order(pdf_files, xml_files):
    """将PDF和XML文件按订单匹配"""
    orders = {}
    
    # 处理XML文件
    for xml_path in xml_files:
        order_id = extract_order_id(xml_path)
        amount = extract_amount_from_xml(xml_path)
        
        if order_id not in orders:
            orders[order_id] = {'xml': xml_path, 'amount': amount, 'pdfs': {'invoice': None, 'itinerary': None}}
        else:
            orders[order_id]['xml'] = xml_path
            orders[order_id]['amount'] = amount
    
    # 处理PDF文件
    for pdf_path in pdf_files:
        order_id = extract_order_id(pdf_path)
        pdf_type = identify_pdf_type(pdf_path)
        
        if pdf_type != 'unknown':
            if order_id not in orders:
                orders[order_id] = {'xml': None, 'amount': 0, 'pdfs': {'invoice': None, 'itinerary': None}}
            
            orders[order_id]['pdfs'][pdf_type] = pdf_path
    
    return orders

def merge_pdfs(itinerary_path, invoice_path, output_path):
    """合并行程单和发票PDF"""
    output = PdfWriter()
    
    # 添加行程单（在前）
    if itinerary_path:
        itinerary = PdfReader(itinerary_path)
        for page in itinerary.pages:
            output.add_page(page)
    
    # 添加发票（在后）
    if invoice_path:
        invoice = PdfReader(invoice_path)
        for page in invoice.pages:
            output.add_page(page)
    
    # 保存合并后的PDF
    with open(output_path, "wb") as output_file:
        output.write(output_file)
    
    return output_path

def process_pdf_files(extract_dir):
    """处理解压后的PDF和XML文件"""
    # 获取所有文件路径
    file_paths = get_file_paths(extract_dir)
    grouped_files = group_files_by_type(file_paths)
    
    # 按订单匹配文件
    orders = match_files_by_order(grouped_files['pdf'], grouped_files['xml'])
    
    results = []
    
    # 处理每个订单
    for order_id, order_data in orders.items():
        # 检查是否有足够的文件进行处理
        itinerary_path = order_data['pdfs']['itinerary']
        invoice_path = order_data['pdfs']['invoice']
        
        if not itinerary_path and not invoice_path:
            continue
        
        # 生成输出文件名
        output_filename = f"order_{order_id}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
        
        # 合并PDF
        merge_pdfs(itinerary_path, invoice_path, output_path)
        
        # 添加处理结果
        results.append({
            'order_id': order_id,
            'amount': order_data['amount'],
            'output_file': output_filename,
            'has_itinerary': itinerary_path is not None,
            'has_invoice': invoice_path is not None
        })
    
    return results 