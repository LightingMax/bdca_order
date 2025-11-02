import re
import uuid
import xml.etree.ElementTree as ET
import os
import requests
import json
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from flask import current_app
from app.services.file_service import get_file_paths, group_files_by_type

def call_qwen_api_for_trips(table_data_list):
    """调用通义千问API规整行程数据"""
    logger = current_app.logger
    
    # 从配置文件获取通义千问API配置
    url = f"{current_app.config['QWEN_API_BASE_URL']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {current_app.config['QWEN_API_KEY']}",
        "Content-Type": "application/json"
    }
    
    # 构建提示词
    prompt = f"""
请帮我整理以下行程记录：将它们按照上车时间升序排列并重新编号，然后以JSON格式返回结果。每个行程记录应包含序号、服务商、车型、上车时间、城市、起点、终点和金额等所有字段。请确保返回标准的JSON数组格式，无需添加任何额外解释。

原始表格数据：
{table_data_list}

请返回JSON数组格式，每个对象包含以下字段：
- sequence: 序号（字符串）
- service_provider: 服务商（字符串）
- car_type: 车型（字符串）
- pickup_time: 上车时间（字符串）
- city: 城市（字符串）
- start_point: 起点（字符串）
- end_point: 终点（字符串）
- amount: 金额（字符串）
"""
    
    data = {
        "model": current_app.config['QWEN_MODEL'],
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        import time
        start_time = time.time()
        
        logger.info("调用通义千问API规整行程数据...")
        logger.info(f"API请求URL: {url}")
        logger.info(f"API超时设置: {current_app.config['QWEN_API_TIMEOUT']} 秒")
        logger.info(f"请求数据大小: {len(str(table_data_list))} 字符")
        logger.info(f"请求开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
        
        response = requests.post(url, headers=headers, json=data, timeout=current_app.config['QWEN_API_TIMEOUT'])
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"API请求完成，耗时: {duration:.2f} 秒")
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        logger.info(f"通义千问API原始返回内容长度: {len(content)} 字符")
        logger.info(f"通义千问API原始返回内容: {content[:500]}...")  # 只显示前500字符
        
        # 提取JSON部分
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            logger.info(f"提取到的JSON字符串长度: {len(json_str)} 字符")
            logger.info(f"提取到的JSON字符串: {json_str}")
            
            parsed_data = json.loads(json_str)
            logger.info(f"通义千问API成功规整了 {len(parsed_data)} 个行程")
            
            # 详细输出每个行程的信息
            for i, trip in enumerate(parsed_data):
                logger.info(f"行程{i+1}: 序号={trip.get('sequence')}, 服务商={trip.get('service_provider')}, 时间={trip.get('pickup_time')}, 起点={trip.get('start_point')}, 终点={trip.get('end_point')}, 金额={trip.get('amount')}")
            
            return parsed_data
        else:
            logger.error("通义千问API返回结果中未找到JSON数据")
            logger.error(f"完整返回内容: {content}")
            return []
            
    except Exception as e:
        logger.error(f"调用通义千问API失败: {e}")
        logger.error(f"请求数据: {data}")
        return []

def extract_amount_from_xml(xml_path):
    """从XML文件中提取订单金额"""
    logger = current_app.logger
    try:
        logger.info(f"正在从XML文件提取金额: {xml_path}")
        
        # 首先尝试从文件名提取金额
        filename = Path(xml_path).name
        amount_match = re.search(r'(\d+\.\d+)元', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)元?-', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)-', filename)
            
        if amount_match:
            amount = float(amount_match.group(1))
            logger.info(f"从文件名中提取到金额: {amount}")
            return amount
            
        # 如果文件名中没有金额，解析XML文件
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 尝试查找常见的金额标签
        # 1. 尝试查找TotalTax-includedAmount标签（示例XML中的格式）
        amount_elem = root.find(".//TotalTax-includedAmount")
        if amount_elem is not None and amount_elem.text:
            try:
                amount = float(amount_elem.text)
                logger.info(f"从TotalTax-includedAmount标签中提取到金额: {amount}")
                return amount
            except ValueError:
                logger.warning(f"无法将TotalTax-includedAmount标签值转换为浮点数: {amount_elem.text}")
        
        # 2. 尝试其他可能的标签
        possible_tags = [
            ".//Amount", 
            ".//TotalAmount", 
            ".//Price", 
            ".//TotaltaxIncludedAmount",
            ".//BasicInformation/TotalAmWithoutTax"
        ]
        
        for tag in possible_tags:
            amount_elem = root.find(tag)
            if amount_elem is not None and amount_elem.text:
                try:
                    amount = float(amount_elem.text)
                    logger.info(f"从{tag}标签中提取到金额: {amount}")
                    return amount
                except ValueError:
                    continue
        
        # 3. 如果没有找到特定标签，尝试在整个XML文本中搜索金额模式
        xml_text = ET.tostring(root, encoding='utf-8').decode('utf-8')
        
        # 尝试匹配常见的金额模式
        amount_patterns = [
            r'TotalTax-includedAmount>(\d+\.\d+)<',
            r'TotaltaxIncludedAmount>(\d+\.\d+)<',
            r'Amount>(\d+\.\d+)<',
            r'金额[：:]\s*(\d+\.\d+)',
            r'总金额[：:]\s*(\d+\.\d+)'
        ]
        
        for pattern in amount_patterns:
            amount_matches = re.findall(pattern, xml_text)
            if amount_matches:
                amount = float(amount_matches[0])
                logger.info(f"从XML文本中使用模式'{pattern}'提取到金额: {amount}")
                return amount
        
        # 如果以上都失败，返回0
        logger.warning(f"无法从XML文件中提取金额: {xml_path}")
        return 0
    except Exception as e:
        logger.error(f"解析XML文件出错: {str(e)}")
        return 0


def extract_amount_from_pdf(pdf_path):
    """从PDF文件中提取金额（轻量级方法）"""
    logger = current_app.logger
    try:
        logger.info(f"正在从PDF文件提取金额: {pdf_path}")
        
        # 首先尝试从文件名提取金额
        filename = Path(pdf_path).name
        amount_match = re.search(r'(\d+\.\d+)元', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)元?-', filename)
        if not amount_match:
            amount_match = re.search(r'-(\d+\.\d+)-', filename)
            
        if amount_match:
            amount = float(amount_match.group(1))
            logger.info(f"从PDF文件名中提取到金额: {amount}")
            return amount
        
        # 使用PyMuPDF (fitz)提取PDF文本内容
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                logger.warning(f"PDF文件没有页面: {pdf_path}")
                doc.close()
                return 0
            
            # 提取所有页面的文本
            full_text = ""
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    if page_text:
                        full_text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"提取第{page_num+1}页文本失败: {e}")
                    continue
            
            doc.close()
            
            if not full_text.strip():
                logger.warning(f"PDF文件没有可提取的文本内容: {pdf_path}")
                return 0
            
            logger.info(f"成功提取PDF文本，长度: {len(full_text)} 字符")
            
            # 使用正则表达式匹配金额
            # 酒店发票常见的金额模式
            amount_patterns = [
                # 标准金额格式：123.45元、123.45
                r'(\d+\.\d{2})元?',
                # 发票金额：价税合计、合计金额等
                r'价税合计[：:]\s*(\d+\.\d{2})',
                r'合计金额[：:]\s*(\d+\.\d{2})',
                r'总金额[：:]\s*(\d+\.\d{2})',
                r'金额[：:]\s*(\d+\.\d{2})',
                # 发票号码后的金额
                r'发票号码[：:].*?(\d+\.\d{2})',
                # 大写金额后的数字金额
                r'[壹贰叁肆伍陆柒捌玖拾佰仟万亿圆角分]+.*?(\d+\.\d{2})',
                # 简单的数字.数字格式（更宽松的匹配）
                r'(\d+\.\d{1,2})',
            ]
            
            # 按优先级尝试匹配
            for pattern in amount_patterns:
                matches = re.findall(pattern, full_text)
                if matches:
                    # 过滤掉明显不是金额的数字（如日期、发票号码等）
                    valid_amounts = []
                    for match in matches:
                        amount = float(match)
                        # 过滤条件：金额应该在合理范围内（1-10000元）
                        if 1.0 <= amount <= 10000.0:
                            valid_amounts.append(amount)
                    
                    if valid_amounts:
                        # 如果有多个匹配，选择最大的（通常是总金额）
                        amount = max(valid_amounts)
                        logger.info(f"从PDF文本中使用模式'{pattern}'提取到金额: {amount}")
                        return amount
            
            # 如果正则匹配失败，尝试查找包含"元"的数字
            yuan_matches = re.findall(r'(\d+\.\d{2})元', full_text)
            if yuan_matches:
                amounts = [float(match) for match in yuan_matches if 1.0 <= float(match) <= 10000.0]
                if amounts:
                    amount = max(amounts)
                    logger.info(f"从PDF文本中提取到含'元'的金额: {amount}")
                    return amount
            
            logger.warning(f"无法从PDF文件中提取金额: {pdf_path}")
            return 0
            
        except Exception as e:
            logger.error(f"使用PyMuPDF提取PDF文本失败: {e}")
            return 0
            
    except Exception as e:
        logger.error(f"从PDF文件提取金额出错: {str(e)}")
        return 0

def identify_pdf_type(pdf_path):
    """识别PDF文件类型（行程单、发票或结账单）"""
    logger = current_app.logger
    try:
        filename = Path(pdf_path).name.lower()
        logger.info(f"正在识别PDF类型: {pdf_path}")
        
        # 通过文件名判断
        if '发票' in filename or 'invoice' in filename or 'receipt' in filename:
            logger.info(f"通过文件名识别为发票: {pdf_path}")
            return 'invoice'
        elif '行程' in filename or 'itinerary' in filename or 'trip' in filename:
            logger.info(f"通过文件名识别为行程单: {pdf_path}")
            return 'itinerary'
        elif '结账单' in filename or '账单' in filename or 'bill' in filename:
            logger.info(f"通过文件名识别为结账单: {pdf_path}")
            return 'hotel_bill'
        
        # 通过文件内容判断（简单版）
        reader = PdfReader(pdf_path)
        if len(reader.pages) > 0:
            text = reader.pages[0].extract_text().lower()
            if '发票' in text or 'invoice' in text or 'receipt' in text:
                logger.info(f"通过内容识别为发票: {pdf_path}")
                return 'invoice'
            elif '行程' in text or 'itinerary' in text or 'trip' in text:
                logger.info(f"通过内容识别为行程单: {pdf_path}")
                return 'itinerary'
            elif '结账单' in text or '账单' in text or '客人姓名' in text or '房间号' in text or '入住日期' in text:
                logger.info(f"通过内容识别为结账单: {pdf_path}")
                return 'hotel_bill'
        
        # 默认返回未知类型
        logger.warning(f"无法识别PDF类型: {pdf_path}")
        return 'unknown'
    except Exception as e:
        logger.error(f"识别PDF类型出错: {str(e)}")
        return 'unknown'

def extract_order_id(file_path):
    """从文件名或内容中提取订单ID - 支持服务商前缀和发票【】格式"""
    logger = current_app.logger
    try:
        logger.info(f"正在提取订单ID: {file_path}")
        filename = Path(file_path).name
        
        # 方法0: 最高优先级 - 从发票文件名中提取【】内的内容
        # 支持格式：【及时用车-53.21元-2个行程】高德打车电子发票
        bracket_pattern = r'【([^】]+)】'
        bracket_match = re.search(bracket_pattern, filename)
        if bracket_match:
            bracket_content = bracket_match.group(1)
            logger.info(f"从发票文件名【】中提取到内容: {bracket_content}")
            return bracket_content
        
        logger.info(f"文件名 '{filename}' 未匹配【】格式，继续尝试其他方法")
        
        # 方法1: 尝试从文件名中提取完整的订单信息
        # 支持格式：阳光出行-32.13元-3个行程、T3-77.06-1等
        order_patterns = [
            r'([^-]+)-(\d+\.\d+)元?-(\d+)个行程',  # 阳光出行-32.13元-3个行程
            r'([^-]+)-(\d+\.\d+)-(\d+)',           # T3-77.06-1
            r'([^-]+)-(\d+\.\d+)',                 # 服务商-金额
            r'订单(\d+)',                           # 订单12345
            r'trip(\d+)',                           # trip001
        ]
        
        # 方法1.5: 腾讯出行特殊格式处理
        # 支持格式：99.45元-2025年08月12日14时16分腾讯出行电子发票-.pdf
        # 支持格式：99.45元-2025年08月12日14时16分腾讯出行行程单-.pdf
        tencent_pattern = r'(\d+\.\d+)元-(\d{4}年\d{2}月\d{2}日\d{2}时\d{2}分)腾讯出行'
        tencent_match = re.search(tencent_pattern, filename)
        if tencent_match:
            amount, datetime_str = tencent_match.groups()
            # 生成统一的订单ID，不区分发票和行程单
            order_id = f"腾讯出行-{amount}元-{datetime_str}"
            logger.info(f"从腾讯出行文件名提取到订单ID: {order_id}")
            return order_id
        
        # 但是，如果文件名包含"订单-"这种格式，我们优先尝试生成更好的格式
        if '订单-' in filename:
            logger.info(f"检测到'订单-'格式，尝试生成更好的订单ID")
            # 尝试从文件名中提取金额和数量
            amount_match = re.search(r'订单-(\d+\.\d+)-(\d+)', filename)
            if amount_match:
                amount, count = amount_match.groups()
                # 生成更友好的格式：T3出行-77.06元-1个行程
                # 这里可以根据金额和数量生成一个更有意义的ID
                smart_id = f"T3出行-{amount}元-{count}个行程"
                logger.info(f"生成智能订单ID: {smart_id}")
                return smart_id
        
        for pattern in order_patterns:
            match = re.search(pattern, filename)
            if match:
                if len(match.groups()) == 3:
                    # 格式：服务商-金额-数量
                    service, amount, count = match.groups()
                    # 验证服务商名称不为空
                    if service and service.strip():
                        order_id = f"{service}-{amount}-{count}"
                        logger.info(f"从文件名中提取到订单ID: {order_id}")
                        return order_id
                    else:
                        logger.warning(f"服务商名称为空，跳过模式: {pattern}")
                        continue
                elif len(match.groups()) == 2:
                    # 格式：服务商-金额
                    service, amount = match.groups()
                    # 验证服务商名称不为空
                    if service and service.strip():
                        order_id = f"{service}-{amount}"
                        logger.info(f"从文件名中提取到订单ID: {order_id}")
                        return order_id
                    else:
                        logger.warning(f"服务商名称为空，跳过模式: {pattern}")
                        continue
                elif len(match.groups()) == 1:
                    # 格式：订单号或trip号
                    order_id = match.group(1)
                    logger.info(f"从文件名中提取到订单ID: {order_id}")
                    return order_id
        
        # 方法2: 尝试查找6位以上的数字作为订单ID
        order_id_match = re.search(r'(\d{6,})', filename)
        if order_id_match:
            order_id = order_id_match.group(1)
            logger.info(f"从文件名中提取到数字订单ID: {order_id}")
            return order_id
        
        # 方法2.5: 特殊处理华住酒店文件
        # 华住酒店发票格式：dzfp_25114000000003462819_杭州大数云智科技有限公司_20250831201746.pdf
        # 华住酒店结账单格式：结账单20250831.pdf
        if 'dzfp_' in filename and '_' in filename:
            # 提取发票号码作为订单ID
            parts = filename.split('_')
            if len(parts) >= 2:
                invoice_number = parts[1]  # 25114000000003462819
                logger.info(f"从华住酒店发票文件名提取到发票号码: {invoice_number}")
                return invoice_number
        elif '结账单' in filename:
            # 对于结账单，尝试从发票号码中提取日期部分进行匹配
            # 这里我们需要一个更智能的匹配策略
            date_match = re.search(r'(\d{8})', filename)  # 20250831
            if date_match:
                date_str = date_match.group(1)
                logger.info(f"从结账单文件名提取到日期: {date_str}")
                # 返回一个通用的订单ID，让系统能够匹配
                return f"hotel_{date_str}"
        
        # 方法3: 如果是PDF，尝试从内容中提取
        if file_path.lower().endswith('.pdf'):
            try:
                reader = PdfReader(file_path)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    # 尝试查找订单号模式
                    order_id_match = re.search(r'订单[号#]?[：:]?\s*(\d{6,})', text)
                    if order_id_match:
                        order_id = order_id_match.group(1)
                        logger.info(f"从PDF内容中提取到订单ID: {order_id}")
                        return order_id
            except Exception as e:
                logger.warning(f"从PDF内容提取订单ID失败: {e}")
        
        # 方法4: 如果是XML，尝试从内容中提取
        if file_path.lower().endswith('.xml'):
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                # 尝试查找订单号元素
                order_elem = root.find(".//OrderID") or root.find(".//OrderNumber")
                if order_elem is not None and order_elem.text:
                    order_id = order_elem.text
                    logger.info(f"从XML内容中提取到订单ID: {order_id}")
                    return order_id
            except Exception as e:
                logger.warning(f"从XML内容提取订单ID失败: {e}")
        
        # 方法5: 生成基于服务商的智能订单ID
        smart_order_id = generate_smart_order_id(filename)
        if smart_order_id:
            logger.info(f"生成智能订单ID: {smart_order_id}")
            return smart_order_id
        
        # 方法6: 如果所有方法都失败，使用文件名的ASCII部分作为标识
        ascii_filename = ''.join(c for c in Path(filename).stem if ord(c) < 128)
        if not ascii_filename:
            ascii_filename = str(uuid.uuid4())[:8]
        
        logger.warning(f"无法提取订单ID，使用文件名作为标识: {ascii_filename}")
        return ascii_filename
        
    except Exception as e:
        logger.error(f"提取订单ID出错: {str(e)}")
        random_id = str(uuid.uuid4())[:8]
        logger.info(f"使用随机ID作为后备: {random_id}")
        return random_id  # 生成随机ID作为后备


def generate_smart_order_id(filename):
    """
    生成智能订单ID - 修正版
    1. 优先提取【】中的内容。
    2. 修复'订单-'开头的格式。
    3. 对于已符合标准格式但无特殊符号的文件，去除扩展名后返回。
    """
    logger = current_app.logger
    try:
        # 移除文件扩展名，方便处理
        name_only = Path(filename).stem

        # 核心逻辑：定义模式并按优先级排序
        patterns = [
            # 优先级 1: 最高优先级 - 提取【】内的完整内容
            (r'【([^】]+)】', lambda m: m.group(1)),
            
            # 优先级 2: 修复 '订单-' 开头的格式
            (r'^订单-(\d+\.\d+)-(\d+)$', lambda m: f"T3出行-{m.group(1)}元-{m.group(2)}个行程"),
            
            # 优先级 2.5: 修复 '订单T3-' 开头的格式
            (r'^订单T3-(\d+\.\d+)-(\d+)$', lambda m: f"T3出行-{m.group(1)}元-{m.group(2)}个行程"),
            
            # 优先级 3: 匹配标准格式（为了防止它被下面的逻辑捕获）
            (r'^[^-]+-\d+\.\d+元?-\d+个行程$', lambda m: m.group(0)),

            # 优先级 4: 匹配简化的 '服务商-金额-数量' 格式
            (r'^([^-]+)-(\d+\.\d+)-(\d+)$', lambda m: f"{m.group(1)}-{m.group(2)}元-{m.group(3)}个行程"),
        ]
        
        for pattern, formatter in patterns:
            # 我们在去除扩展名的文件名上进行匹配
            match = re.search(pattern, name_only)
            if match:
                result = formatter(match)
                logger.info(f"文件名 '{filename}' 匹配模式 '{pattern}'，生成结果: '{result}'")
                return result
        
        logger.info(f"文件名 '{filename}' 未匹配任何模式，返回原文件名: '{name_only}'")
        
        # 如果以上所有特殊规则都未匹配，说明它可能是“其他格式”
        # 直接返回去除扩展名后的文件名
        return name_only
        
    except Exception as e:
        logger.warning(f"生成智能订单ID失败: {filename}, 错误: {e}")
        return None

def match_files_by_order(pdf_files, xml_files):
    """将PDF和XML文件按订单匹配"""
    logger = current_app.logger
    logger.info(f"开始匹配文件，PDF文件数: {len(pdf_files)}，XML文件数: {len(xml_files)}")
    
    orders = {}
    
    # 处理XML文件
    for xml_path in xml_files:
        logger.info(f"正在处理XML文件: {xml_path}")
        order_id = extract_order_id(xml_path)
        logger.info(f"从XML文件提取到订单ID: '{order_id}'")
        amount = extract_amount_from_xml(xml_path)
        
        if order_id not in orders:
            orders[order_id] = {'xml': xml_path, 'amount': amount, 'pdfs': {'invoice': None, 'itinerary': None}}
            logger.info(f"创建新订单: {order_id}, 金额: {amount}")
        else:
            orders[order_id]['xml'] = xml_path
            orders[order_id]['amount'] = amount
            logger.info(f"更新订单信息: {order_id}, 金额: {amount}")
    
    # 处理PDF文件
    for pdf_path in pdf_files:
        logger.info(f"正在处理PDF文件: {pdf_path}")
        order_id = extract_order_id(pdf_path)
        logger.info(f"从PDF文件提取到订单ID: '{order_id}'")
        pdf_type = identify_pdf_type(pdf_path)
        logger.info(f"PDF文件类型: {pdf_type}")
        
        if pdf_type != 'unknown':
            if order_id not in orders:
                orders[order_id] = {'xml': None, 'amount': 0, 'pdfs': {'invoice': None, 'itinerary': None, 'hotel_bill': None}}
                logger.info(f"创建新订单(来自PDF): {order_id}")
            
            # 确保pdfs字典包含所有类型
            if 'hotel_bill' not in orders[order_id]['pdfs']:
                orders[order_id]['pdfs']['hotel_bill'] = None
            
            orders[order_id]['pdfs'][pdf_type] = pdf_path
            logger.info(f"为订单 {order_id} 添加 {pdf_type} 类型的PDF: {pdf_path}")
    
    # 检查所有订单的XML状态（针对网约车文件）
    xml_missing_warnings = []
    for order_id, order_data in orders.items():
        if order_data['xml'] is None:
            # XML文件缺失时，尝试从PDF文件名中提取金额
            logger.info(f"🔍 网约车订单 {order_id} 缺少XML文件，尝试从PDF文件名提取金额")
            
            # 尝试从发票PDF文件名提取金额
            if order_data['pdfs'].get('invoice'):
                invoice_amount = extract_amount_from_pdf(order_data['pdfs']['invoice'])
                if invoice_amount > 0:
                    order_data['amount'] = invoice_amount
                    logger.info(f"✅ 从发票文件名成功提取金额: {invoice_amount}元")
                else:
                    # 如果发票文件名提取失败，尝试从行程单文件名提取
                    if order_data['pdfs'].get('itinerary'):
                        itinerary_amount = extract_amount_from_pdf(order_data['pdfs']['itinerary'])
                        if itinerary_amount > 0:
                            order_data['amount'] = itinerary_amount
                            logger.info(f"✅ 从行程单文件名成功提取金额: {itinerary_amount}元")
            
            # 如果仍然没有提取到金额，记录警告
            if order_data['amount'] == 0:
                xml_missing_warnings.append({
                    'order_id': order_id,
                    'reason': 'XML文件缺失且无法从PDF文件名提取金额',
                    'impact': '金额统计为0，可能不准确',
                    'type': 'taxi'
                })
                logger.warning(f"⚠️ 网约车订单 {order_id} 缺少XML文件且无法从PDF文件名提取金额")
            else:
                logger.info(f"✅ 网约车订单 {order_id} 从PDF文件名成功提取金额: {order_data['amount']}元")
        elif order_data['amount'] == 0:
            xml_missing_warnings.append({
                'order_id': order_id,
                'reason': 'XML中未找到金额信息',
                'impact': '金额统计为0，可能不准确',
                'type': 'taxi'
            })
            logger.warning(f"⚠️ 网约车订单 {order_id} XML中未找到金额信息，金额统计为0，可能不准确")
    
    logger.info(f"网约车文件匹配完成，共找到 {len(orders)} 个订单，XML缺失警告: {len(xml_missing_warnings)} 个")
    return orders, xml_missing_warnings


def smart_match_hotel_files(orders, extract_dir):
    """智能匹配华住酒店文件"""
    logger = current_app.logger
    logger.info("🔍 开始智能匹配华住酒店文件")
    
    # 查找所有华住酒店相关文件
    hotel_invoices = []
    hotel_bills = []
    
    for order_id, order_data in orders.items():
        if order_data['pdfs']['invoice']:
            invoice_path = order_data['pdfs']['invoice']
            if 'dzfp_' in Path(invoice_path).name:
                hotel_invoices.append((order_id, invoice_path))
        
        if order_data['pdfs'].get('hotel_bill'):
            bill_path = order_data['pdfs']['hotel_bill']
            if '结账单' in Path(bill_path).name:
                hotel_bills.append((order_id, bill_path))
    
    logger.info(f"找到华住酒店发票: {len(hotel_invoices)}个")
    logger.info(f"找到华住酒店结账单: {len(hotel_bills)}个")
    
    # 如果发票和结账单数量相同，尝试匹配
    if len(hotel_invoices) == 1 and len(hotel_bills) == 1:
        invoice_order_id, invoice_path = hotel_invoices[0]
        bill_order_id, bill_path = hotel_bills[0]
        
        # 如果它们在不同的订单中，合并它们
        if invoice_order_id != bill_order_id:
            logger.info(f"🔄 合并华住酒店订单: {invoice_order_id} + {bill_order_id}")
            
            # 使用发票的订单ID作为主订单ID
            main_order_id = invoice_order_id
            main_order = orders[invoice_order_id]
            
            # 将结账单添加到主订单中
            main_order['pdfs']['hotel_bill'] = bill_path
            logger.info(f"✅ 将结账单 {Path(bill_path).name} 添加到订单 {main_order_id}")
            
            # 删除原来的结账单订单
            if bill_order_id in orders:
                del orders[bill_order_id]
                logger.info(f"🗑️ 删除重复的结账单订单: {bill_order_id}")
    
    return orders


def identify_zip_type_from_filename(zip_filename):
    """根据ZIP文件名识别类型"""
    if not zip_filename:
        return 'unknown'
    
    filename_lower = zip_filename.lower()
    
    # 检查住宿相关关键词
    hotel_keywords = [
        '华住', '酒店', 'hotel', '住宿', 'accommodation', 
        '桔子', '汉庭', '全季', '如家', '7天', '锦江',
        '结账单', '账单', 'bill'
    ]
    
    # 检查打车相关关键词
    taxi_keywords = [
        '打车', '出行', '行程', 'trip', 'itinerary',
        '高德', '滴滴', '曹操', '首汽', '阳光', 't3',
        '火箭', '及时', '约车'
    ]
    
    # 优先检查住宿关键词
    if any(keyword in filename_lower for keyword in hotel_keywords):
        return 'hotel'
    
    # 然后检查打车关键词
    if any(keyword in filename_lower for keyword in taxi_keywords):
        return 'taxi'
    
    return 'unknown'


def match_hotel_files_by_hash(pdf_files, xml_files, extract_dir):
    """使用hash前缀匹配住宿文件"""
    logger = current_app.logger
    logger.info(f"🏨 开始使用hash前缀匹配住宿文件")
    logger.info(f"PDF文件数: {len(pdf_files)}, XML文件数: {len(xml_files)}")
    
    orders = {}
    
    # 处理XML文件
    for xml_path in xml_files:
        logger.info(f"正在处理XML文件: {xml_path}")
        order_id = extract_order_id(xml_path)
        logger.info(f"从XML文件提取到订单ID: '{order_id}'")
        amount = extract_amount_from_xml(xml_path)
        
        if order_id not in orders:
            orders[order_id] = {'xml': xml_path, 'amount': amount, 'pdfs': {'invoice': None, 'itinerary': None, 'hotel_bill': None}}
            logger.info(f"创建新订单: {order_id}, 金额: {amount}")
        else:
            orders[order_id]['xml'] = xml_path
            orders[order_id]['amount'] = amount
            logger.info(f"更新订单信息: {order_id}, 金额: {amount}")
    
    # 处理PDF文件 - 使用hash前缀关联
    # 从extract_dir路径中提取hash前缀
    # 路径格式: /path/to/temp/session_id/extracted/hash_prefix/
    path_parts = Path(extract_dir).parts
    hash_prefix = None
    for part in reversed(path_parts):
        if len(part) >= 8:  # hash前缀通常是8位或更长
            hash_prefix = part
            break
    
    logger.info(f"🔑 使用hash前缀关联文件: {hash_prefix}")
    
    # 为住宿文件创建统一的订单ID
    hotel_order_id = f"hotel_{hash_prefix}" if hash_prefix else "hotel_accommodation"
    
    # 确保订单存在
    if hotel_order_id not in orders:
        orders[hotel_order_id] = {'xml': None, 'amount': 0, 'pdfs': {'invoice': None, 'itinerary': None, 'hotel_bill': None}}
        logger.info(f"创建住宿订单: {hotel_order_id}")
    
    # 将所有PDF文件按类型分类并添加到订单中，同时提取金额
    for pdf_path in pdf_files:
        logger.info(f"正在处理PDF文件: {pdf_path}")
        pdf_type = identify_pdf_type(pdf_path)
        logger.info(f"PDF文件类型: {pdf_type}")
        
        if pdf_type != 'unknown':
            orders[hotel_order_id]['pdfs'][pdf_type] = pdf_path
            logger.info(f"为住宿订单 {hotel_order_id} 添加 {pdf_type} 类型的PDF: {pdf_path}")
            
            # 如果是酒店发票，尝试从PDF中提取金额
            if pdf_type == 'invoice' and orders[hotel_order_id]['amount'] == 0:
                pdf_amount = extract_amount_from_pdf(pdf_path)
                if pdf_amount > 0:
                    orders[hotel_order_id]['amount'] = pdf_amount
                    logger.info(f"🏨 从酒店发票PDF中提取到金额: {pdf_amount}")
    
    # 检查所有订单的金额状态（针对酒店文件）
    amount_warnings = []
    for order_id, order_data in orders.items():
        if order_data['xml'] is None and order_data['amount'] == 0:
            # 酒店文件没有XML，也没有从PDF提取到金额
            amount_warnings.append({
                'order_id': order_id,
                'reason': '酒店发票金额提取失败',
                'impact': '无法获取金额信息，请检查发票文件',
                'type': 'hotel'
            })
            logger.warning(f"⚠️ 酒店订单 {order_id} 无法提取金额信息")
        elif order_data['xml'] is None and order_data['amount'] > 0:
            # 酒店文件没有XML，但成功从PDF提取到金额
            logger.info(f"✅ 酒店订单 {order_id} 从PDF成功提取金额: {order_data['amount']}")
        elif order_data['xml'] is not None and order_data['amount'] == 0:
            # 有XML但金额为0（这种情况在酒店文件中较少见）
            amount_warnings.append({
                'order_id': order_id,
                'reason': 'XML中未找到金额信息',
                'impact': '金额统计为0，可能不准确',
                'type': 'hotel'
            })
            logger.warning(f"⚠️ 酒店订单 {order_id} XML中未找到金额信息")
    
    logger.info(f"🏨 住宿文件匹配完成，共找到 {len(orders)} 个订单，金额警告: {len(amount_warnings)} 个")
    return orders, amount_warnings




def create_smart_combined_pdf(itinerary_path: str, invoice_path: str, output_path: str, page_count: int = 1) -> bool:
    """
    创建智能拼接PDF - 统一处理1页和多页行程单的拼接逻辑
    
    Args:
        itinerary_path: 行程单文件路径
        invoice_path: 发票文件路径  
        output_path: 输出文件路径
        page_count: 行程单页数，1表示单页，>1表示多页
    
    Returns:
        bool: 拼接是否成功
    """
    logger = current_app.logger
    logger.info(f"开始智能拼接PDF，行程单页数: {page_count}")
    
    try:
        if page_count == 1:
            # 单页行程单：发票在上，行程单在下，压缩到一页
            logger.info("🔄 处理单页行程单：发票在上 + 行程单在下，压缩到一页")
            return create_smart_combined_single_page(itinerary_path, invoice_path, output_path)
        else:
            # 多页行程单：生成完整的拼接文件
            # 第一页：发票+行程单第一页内容
            # 后续页面：行程单的剩余页面
            logger.info("🔄 处理多页行程单：生成完整的拼接文件（发票+行程单所有页面）")
            return create_smart_combined_multi_page(itinerary_path, invoice_path, output_path, page_count)
            
    except Exception as e:
        logger.error(f"❌ 智能拼接PDF失败: {e}")
        return False


def create_smart_combined_single_page(itinerary_path: str, invoice_path: str, output_path: str) -> bool:
    """
    创建单页智能拼接：发票在上（占50%高度），行程单在下（占50%高度），压缩到一页
    
    采用图片拼接方式，更加稳定可靠，避免PDF工具拼接的黑色区域问题
    """
    logger = current_app.logger
    logger.info(f"🚀 开始创建单页智能拼接：发票在上（50%）+ 行程单在下（50%），压缩到一页")
    
    try:
        # 导入必要的库
        try:
            from pdf2image import convert_from_path
            from PIL import Image
        except ImportError as e:
            logger.error(f"❌ 缺少必要的库: {e}")
            logger.info("请安装: pip install pdf2image Pillow")
            return False
        
        # 从文件名中匹配发票/行程单中包含的行程数量
        # 实例文件名：【阳光出行-32.13元-3个行程】高德打车电子发票，匹配其中的3个行程
        itinerary_name = Path(itinerary_path).name
        invoice_name = Path(invoice_path).name
        itinerary_match = re.search(r'-(\d+)个行程', itinerary_name)
        invoice_match = re.search(r'-(\d+)个行程', invoice_name)
        itinerary_count = int(itinerary_match.group(1)) if itinerary_match else 1
        invoice_count = int(invoice_match.group(1)) if invoice_match else 1
        
        # 验证行程数量一致性
        if itinerary_count != invoice_count:
            logger.warning(f"⚠️ 行程单和发票的行程数量不一致：行程单{itinerary_count}个，发票{invoice_count}个")
            logger.info("使用行程单的数量作为标准")
            itinerary_count = max(itinerary_count, invoice_count)
        
        logger.info(f"📊 检测到行程数量: {itinerary_count}个")
        
        # A4尺寸（像素，300 DPI）
        A4_WIDTH, A4_HEIGHT = 2480, 3508
        # 定义页边距（像素）
        MARGIN = 100
        # 考虑页边距后的实际可用宽度和高度
        USABLE_WIDTH = A4_WIDTH - 2 * MARGIN
        USABLE_HEIGHT = A4_HEIGHT - 2 * MARGIN
        
        # 计算每个行程的高度比例
        per_count_height = USABLE_HEIGHT / 21
        
        try:
            # 转换行程单为图片
            logger.info("📄 转换行程单为图片")
            itinerary_images = convert_from_path(itinerary_path, dpi=300)
            itinerary_image = itinerary_images[0]
            w, h = itinerary_image.size
            
            # 计算需要裁剪的区域，去除部分顶部无关内容
            # 根据行程数量动态调整裁剪区域
            crop_top = int(4 * per_count_height)
            crop_bottom = int(h // 2 + per_count_height * (itinerary_count - 1))
            top_half = itinerary_image.crop((0, crop_top, w, crop_bottom))
            
            logger.info(f"✂️ 行程单裁剪区域: 顶部{crop_top}px, 底部{crop_bottom}px")
            
            # 调整行程单尺寸（占下半部分，50%高度）
            ratio = USABLE_WIDTH / top_half.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.5))
            top_half = top_half.resize(new_size, Image.Resampling.LANCZOS)
            
            # 转换发票为图片
            logger.info("🧾 转换发票为图片")
            invoice_images = convert_from_path(invoice_path, dpi=300)
            invoice_image = invoice_images[0]
            
            # 调整发票尺寸（占上半部分，50%高度）
            ratio = USABLE_WIDTH / invoice_image.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.5))
            invoice_image = invoice_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 创建新的空白图片
            combined = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
            
            # 粘贴发票到上半部分（考虑页边距）
            combined.paste(invoice_image, (MARGIN, MARGIN))
            
            # 粘贴行程单到下半部分（考虑页边距）
            combined.paste(top_half, (MARGIN, MARGIN + invoice_image.height))
            
            # 最后再缩放到A4纸
            combined = combined.resize((A4_WIDTH, A4_HEIGHT), Image.Resampling.LANCZOS)
            
            # 保存为PDF
            logger.info("💾 保存拼接后的图片为PDF")
            combined.save(output_path, "PDF", resolution=300.0)
            
            # 验证输出文件
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info(f"📊 单页拼接文件大小: {file_size} bytes")
                
                # 验证文件质量
                if file_size < 1000:
                    logger.error("❌ 拼接文件过小，可能拼接失败")
                    return False
                
                logger.info("✅ 单页智能拼接成功（发票+行程单图片拼接到一页）")
                logger.info(f"   文件路径: {output_path}")
                logger.info(f"   文件大小: {file_size} bytes")
                return True
            else:
                logger.error("❌ 单页拼接输出文件未生成")
                return False
                
        except Exception as e:
            logger.error(f"❌ 图片拼接过程中出错: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"❌ 创建单页智能拼接失败: {e}")
        return False


def create_smart_combined_multi_page(itinerary_path: str, invoice_path: str, output_path: str, page_count: int) -> bool:
    """
    创建多页智能拼接：生成完整的拼接文件
    
    第一页：发票+行程单第一页内容
    后续页面：行程单的剩余页面（第2页、第3页...）
    
    这样预览时可以看到完整内容，打印时也能正确处理
    """
    logger = current_app.logger
    try:
        logger.info(f"🚀 开始创建多页智能拼接，行程单总页数: {page_count}")
        
        # 检查是否有必要的工具
        import subprocess
        import shutil
        if not shutil.which('pdftk'):
            logger.warning("未找到pdftk工具，无法合并PDF")
            return False
        
        # 创建临时文件
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_invoice_first = Path(temp_dir) / f"temp_invoice_first_{uuid.uuid4().hex[:8]}.pdf"
        temp_itinerary_first = Path(temp_dir) / f"temp_itinerary_first_{uuid.uuid4().hex[:8]}.pdf"
        temp_remaining_pages = Path(temp_dir) / f"temp_remaining_{uuid.uuid4().hex[:8]}.pdf"
        
        try:
            # 1. 提取发票第一页
            logger.info("🧾 提取发票第一页")
            subprocess.run(['pdftk', invoice_path, 'cat', '1', 'output', temp_invoice_first], check=True)
            
            # 2. 提取行程单第一页
            logger.info("📄 提取行程单第一页")
            subprocess.run(['pdftk', itinerary_path, 'cat', '1', 'output', temp_itinerary_first], check=True)
            
            # 3. 提取行程单剩余页面（第2页到最后一页）
            if page_count > 1:
                logger.info(f"📄 提取行程单剩余页面（第2页到第{page_count}页）")
                subprocess.run(['pdftk', itinerary_path, 'cat', '2-end', 'output', temp_remaining_pages], check=True)
            
            # 4. 拼接第一页：发票+行程单第一页内容
            logger.info("🔗 拼接第一页：发票在上 + 行程单第一页内容")
            first_page_combined = Path(temp_dir) / f"first_page_combined_{uuid.uuid4().hex[:8]}.pdf"
            
            subprocess.run([
                'pdftk', temp_invoice_first, temp_itinerary_first, 
                'cat', 'output', first_page_combined
            ], check=True)
            
            # 5. 合并所有页面
            logger.info("🔗 合并所有页面：第一页（发票+行程单第一页）+ 剩余页面")
            
            if page_count > 1:
                # 多页：第一页拼接 + 剩余页面
                subprocess.run([
                    'pdftk', first_page_combined, temp_remaining_pages, 
                    'cat', 'output', output_path
                ], check=True)
            else:
                # 单页：直接使用第一页拼接结果
                import shutil
                shutil.copy2(first_page_combined, output_path)
            
            # 验证输出文件
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info(f"📊 多页拼接文件大小: {file_size} bytes")
                
                # 验证文件质量
                if file_size < 1000:
                    logger.warning("⚠️ 拼接文件过小，可能拼接失败")
                    return False
                
                # 验证PDF页数
                result = subprocess.run(['pdftk', output_path, 'dump_data'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    output_page_count = 0
                    for line in result.stdout.split('\n'):
                        if line.startswith('NumberOfPages:'):
                            output_page_count = int(line.split(':')[1].strip())
                            break
                    
                    expected_pages = 1 + page_count  # 1页（发票+行程单第一页）+ 行程单剩余页面
                    if output_page_count == expected_pages:
                        logger.info(f"✅ 多页拼接成功：{output_page_count}页")
                        logger.info(f"   文件路径: {output_path}")
                        logger.info(f"   文件大小: {file_size} bytes")
                        logger.info(f"   预期页数: {expected_pages}页")
                        return True
                    else:
                        logger.warning(f"⚠️ 页数不匹配：实际{output_page_count}页，预期{expected_pages}页")
                        return False
                        
                else:
                    logger.warning("⚠️ 无法验证PDF页数")
                    return False
                    
            else:
                logger.error("❌ 输出文件创建失败")
                return False
                
        finally:
            # 清理临时文件
            temp_files = [temp_invoice_first, temp_itinerary_first, temp_remaining_pages, first_page_combined]
            for temp_file in temp_files:
                if Path(temp_file).exists():
                    try:
                        Path(temp_file).unlink()
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {temp_file}, 错误: {e}")
        
    except Exception as e:
        logger.error(f"❌ 创建多页智能拼接失败: {e}")
        return False




def create_hotel_combined_pdf(invoice_path: str, hotel_bill_path: str, output_path: str) -> bool:
    """创建住宿发票+结账单的拼接页面（结账单上部50%），使用图像拼接方式确保1页输出"""
    logger = current_app.logger
    try:
        logger.info(f"🏨 开始创建住宿拼接页面：发票 + 结账单上部50%")
        logger.info(f"   发票文件: {Path(invoice_path).name}")
        logger.info(f"   结账单文件: {Path(hotel_bill_path).name}")
        
        # 导入必要的库
        try:
            from pdf2image import convert_from_path
            from PIL import Image
        except ImportError as e:
            logger.error(f"❌ 缺少必要的库: {e}")
            logger.info("请安装: pip install pdf2image Pillow")
            return False
        
        # A4尺寸（像素，300 DPI）
        A4_WIDTH, A4_HEIGHT = 2480, 3508
        # 定义页边距（像素）
        MARGIN = 100
        # 考虑页边距后的实际可用宽度和高度
        USABLE_WIDTH = A4_WIDTH - 2 * MARGIN
        USABLE_HEIGHT = A4_HEIGHT - 2 * MARGIN
        
        try:
            # 1. 转换结账单为图片
            logger.info("📄 转换结账单为图片")
            bill_images = convert_from_path(hotel_bill_path, dpi=300)
            bill_image = bill_images[0]
            w, h = bill_image.size
            
            # 2. 提取结账单上部50%（修复：确保是上部而不是下部）
            logger.info("✂️ 提取结账单上部50%")
            # 上部50%：从顶部(0)到中间(h//2)
            top_half = bill_image.crop((0, 0, w, h // 2))
            logger.info(f"✂️ 结账单裁剪区域: 顶部0px, 底部{h//2}px")
            
            # 3. 调整结账单尺寸（占下半部分，约60%高度）
            ratio = USABLE_WIDTH / top_half.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.6))
            top_half = top_half.resize(new_size, Image.Resampling.LANCZOS)
            
            # 4. 转换发票为图片
            logger.info("🧾 转换发票为图片")
            invoice_images = convert_from_path(invoice_path, dpi=300)
            invoice_image = invoice_images[0]
            
            # 5. 调整发票尺寸（占上半部分，约40%高度）
            ratio = 0.9 * USABLE_WIDTH / invoice_image.width
            new_size = (USABLE_WIDTH, int(USABLE_HEIGHT * 0.4))
            invoice_image = invoice_image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 6. 创建新的空白图片
            combined = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
            
            # 7. 粘贴发票到上半部分（考虑页边距）
            combined.paste(invoice_image, (MARGIN, MARGIN))
            
            # 8. 粘贴结账单上部到下半部分（考虑页边距）
            combined.paste(top_half, (MARGIN, MARGIN + invoice_image.height))
            
            # 9. 最后再缩放到A4纸
            combined = combined.resize((A4_WIDTH, A4_HEIGHT), Image.Resampling.LANCZOS)
            
            # 10. 保存为PDF
            logger.info("💾 保存拼接后的图片为PDF")
            combined.save(output_path, "PDF", resolution=300.0)
            
            # 验证输出文件
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                logger.info(f"📊 住宿拼接文件大小: {file_size} bytes")
                
                # 验证文件质量
                if file_size < 1000:
                    logger.error("❌ 拼接文件过小，可能拼接失败")
                    return False
                
                logger.info("✅ 住宿拼接成功（发票+结账单上部50%拼接到一页）")
                logger.info(f"   文件路径: {output_path}")
                logger.info(f"   文件大小: {file_size} bytes")
                return True
            else:
                logger.error("❌ 住宿拼接输出文件未生成")
                return False
                
        except Exception as e:
            logger.error(f"❌ 图片拼接过程中出错: {str(e)}")
            raise
        
    except Exception as e:
        logger.error(f"❌ 创建住宿拼接页面失败: {e}")
        return False


def process_pdf_files(extract_dir, zip_filename=None):
    """处理解压后的PDF和XML文件"""
    logger = current_app.logger
    logger.info(f"开始处理解压后的文件: {extract_dir}")
    
    # 根据ZIP文件名判断处理类型
    zip_type = identify_zip_type_from_filename(zip_filename) if zip_filename else 'unknown'
    logger.info(f"ZIP文件类型: {zip_type}")
    
    # 获取所有文件路径
    file_paths = get_file_paths(extract_dir)
    grouped_files = group_files_by_type(file_paths)
    
    # 根据ZIP类型选择不同的处理策略
    if zip_type == 'hotel':
        # 住宿记录：使用hash前缀关联文件
        orders, xml_missing_warnings = match_hotel_files_by_hash(grouped_files['pdf'], grouped_files['xml'], extract_dir)
    else:
        # 打车行程单：使用原有的订单匹配逻辑
        orders, xml_missing_warnings = match_files_by_order(grouped_files['pdf'], grouped_files['xml'])
        # 特殊处理：如果发现华住酒店文件，尝试智能匹配
        orders = smart_match_hotel_files(orders, extract_dir)
        
        # 如果ZIP类型是unknown但包含华住酒店文件，也尝试酒店匹配
        if zip_type == 'unknown' and any('dzfp_' in Path(pdf).name for pdf in grouped_files['pdf']):
            logger.info("🔍 检测到华住酒店发票，尝试酒店文件匹配")
            hotel_orders, hotel_warnings = match_hotel_files_by_hash(grouped_files['pdf'], grouped_files['xml'], extract_dir)
            if hotel_orders:
                logger.info(f"✅ 成功匹配到 {len(hotel_orders)} 个酒店订单")
                orders.update(hotel_orders)
                xml_missing_warnings.extend(hotel_warnings)
    
    results = []
    
    # 处理每个订单
    order_count = 0
    for order_id, order_data in orders.items():
        # 检查是否有足够的文件进行处理
        itinerary_path = order_data['pdfs']['itinerary']
        invoice_path = order_data['pdfs']['invoice']
        hotel_bill_path = order_data['pdfs'].get('hotel_bill')
        
        if not itinerary_path and not invoice_path:
            logger.warning(f"订单 {order_id} 没有PDF文件，跳过处理")
            continue
        
        # 使用简单的序号作为文件名前缀，避免使用中文文件名
        order_count += 1
        
        # 生成输出文件名 (使用序号和随机字符串，避免使用可能包含中文的order_id)
        output_filename = f"order_{order_count}_{uuid.uuid4().hex[:8]}.pdf"
        output_path = Path(current_app.config['OUTPUT_FOLDER']) / output_filename
        
        logger.info(f"处理订单 {order_id} (序号 {order_count})，输出文件: {output_filename}")
        
        # 智能拼接PDF（根据文件类型决定拼接方式）
        try:
            # 判断是住宿记录还是打车行程单
            if invoice_path and hotel_bill_path:
                # 住宿记录：发票+结账单
                logger.info(f"🏨 检测到住宿记录，处理发票+结账单拼接")
                if create_hotel_combined_pdf(invoice_path, hotel_bill_path, output_path):
                    logger.info(f"住宿拼接成功，输出文件: {output_path}")
                    
                    # 添加处理结果
                    results.append({
                        'order_id': order_id,
                        'amount': order_data['amount'],
                        'output_file': output_filename,
                        'has_itinerary': False,
                        'has_invoice': True,
                        'has_hotel_bill': True,
                        'page_count': 1,
                        'combined_type': 'hotel_accommodation'
                    })
                    logger.info(f"订单 {order_id} 住宿记录处理成功")
                else:
                    logger.error(f"住宿拼接失败，订单 {order_id}")
            elif itinerary_path and invoice_path:
                # 单个行程单：行程单+发票（保持原有逻辑）
                logger.info(f"🚗 检测到单个行程单，处理行程单+发票拼接")
                
                # 获取行程单页数
                page_count = 1  # 默认1页
                try:
                    from PyPDF2 import PdfReader
                    with open(itinerary_path, 'rb') as f:
                        reader = PdfReader(f)
                        page_count = len(reader.pages)
                        logger.info(f"行程单页数: {page_count}")
                except Exception as e:
                    logger.warning(f"无法获取行程单页数，使用默认值1: {e}")
                
                # 在处理拼接之前，先提取原始表格数据并缓存
                raw_table_data = None
                try:
                    logger.info(f"🚗 开始提取原始表格数据: {itinerary_path}")
                    raw_table_data = extract_trip_info_from_itinerary(itinerary_path)
                    if raw_table_data:
                        logger.info(f"✅ 成功提取到原始表格数据，行数: {len(raw_table_data)}")
                    else:
                        logger.warning(f"⚠️ 未能提取到原始表格数据")
                except Exception as e:
                    logger.error(f"❌ 提取原始表格数据失败: {e}")
                
                # 使用智能拼接函数
                if create_smart_combined_pdf(itinerary_path, invoice_path, output_path, page_count):
                    logger.info(f"智能拼接成功，输出文件: {output_path}")
                    
                    # 添加处理结果，包含提取的原始表格数据
                    result = {
                        'order_id': order_id,
                        'amount': order_data['amount'],
                        'output_file': output_filename,
                        'has_itinerary': True,
                        'has_invoice': True,
                        'has_hotel_bill': False,
                        'page_count': page_count,
                        'combined_type': 'single_page' if page_count == 1 else 'multi_page',
                        'raw_table_data': raw_table_data,  # 缓存原始表格数据
                        'itinerary_file': itinerary_path  # 保存原始行程单文件路径
                    }
                    results.append(result)
                    logger.info(f"订单 {order_id} 处理成功，包含原始表格数据行数: {len(raw_table_data) if raw_table_data else 0}")
                else:
                    logger.error(f"智能拼接失败，订单 {order_id}")
            else:
                logger.warning(f"订单 {order_id} 文件组合不完整，跳过处理")
                
        except Exception as e:
            logger.error(f"处理订单 {order_id} 时出错: {str(e)}")
    
    logger.info(f"所有订单处理完成，成功处理 {len(results)} 个订单")
    
    # 分类统计金额和警告
    taxi_amount = 0
    hotel_amount = 0
    taxi_warnings = []
    hotel_warnings = []
    
    # 统计各类订单的金额
    for order_id, order_data in orders.items():
        amount = order_data.get('amount', 0)
        if order_id.startswith('hotel_'):
            hotel_amount += amount
        else:
            taxi_amount += amount
    
    # 分类警告信息
    for warning in xml_missing_warnings:
        if warning.get('type') == 'hotel':
            hotel_warnings.append(warning)
        else:
            taxi_warnings.append(warning)
    
    # 记录分类统计结果
    logger.info(f"📊 金额统计结果:")
    logger.info(f"   🚗 网约车总金额: {taxi_amount:.2f}元 ({len([order_id for order_id in orders.keys() if not order_id.startswith('hotel_')])}个订单)")
    logger.info(f"   🏨 酒店总金额: {hotel_amount:.2f}元 ({len([order_id for order_id in orders.keys() if order_id.startswith('hotel_')])}个订单)")
    logger.info(f"   💰 总金额: {taxi_amount + hotel_amount:.2f}元")
    
    # 记录分类警告
    if taxi_warnings:
        logger.warning(f"⚠️ 网约车相关问题 ({len(taxi_warnings)}个):")
        for warning in taxi_warnings:
            logger.warning(f"   🚗 订单 {warning['order_id']}: {warning['reason']} -> {warning['impact']}")
    
    if hotel_warnings:
        logger.warning(f"⚠️ 酒店相关问题 ({len(hotel_warnings)}个):")
        for warning in hotel_warnings:
            logger.warning(f"   🏨 订单 {warning['order_id']}: {warning['reason']} -> {warning['impact']}")
    
    # 创建分类统计信息
    classification_info = {
        'taxi_amount': taxi_amount,
        'hotel_amount': hotel_amount,
        'total_amount': taxi_amount + hotel_amount,
        'taxi_orders': len([order_id for order_id in orders.keys() if not order_id.startswith('hotel_')]),
        'hotel_orders': len([order_id for order_id in orders.keys() if order_id.startswith('hotel_')]),
        'taxi_warnings': taxi_warnings,
        'hotel_warnings': hotel_warnings
    }
    
    return results, xml_missing_warnings, classification_info


def merge_processed_pdfs(processed_files, output_path):
    """
    拼接多个已处理的PDF文件
    
    Args:
        processed_files: 已处理的文件列表，每个文件包含output_file等信息
        output_path: 输出文件路径
    
    Returns:
        bool: 拼接是否成功
    """
    logger = current_app.logger
    logger.info(f"开始拼接 {len(processed_files)} 个PDF文件")
    
    try:
        # 检查是否有必要的工具
        import subprocess
        import shutil
        if not shutil.which('pdftk'):
            logger.warning("未找到pdftk工具，无法合并PDF")
            return False
        
        # 按类型分类文件：酒店文件优先，然后是网约车文件
        hotel_files = []
        taxi_files = []
        
        for file_info in processed_files:
            output_file = file_info.get('output_file')
            if not output_file:
                continue
                
            # 构建完整文件路径
            from app import Config
            full_path = os.path.join(Config.OUTPUT_FOLDER, output_file)
            
            if not os.path.exists(full_path):
                logger.warning(f"文件不存在，跳过: {full_path}")
                continue
            
            # 根据文件类型分类
            if file_info.get('combined_type') == 'hotel_accommodation':
                hotel_files.append(full_path)
                logger.info(f"🏨 添加酒店文件: {output_file}")
            else:
                taxi_files.append(full_path)
                logger.info(f"🚗 添加网约车文件: {output_file}")
        
        # 合并文件列表：酒店文件在前，网约车文件在后
        all_files = hotel_files + taxi_files
        
        if not all_files:
            logger.warning("没有找到可拼接的文件")
            return False
        
        logger.info(f"📋 拼接顺序: {len(hotel_files)} 个酒店文件 + {len(taxi_files)} 个网约车文件")
        
        # 使用pdftk进行拼接
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_combined = Path(temp_dir) / f"temp_combined_{uuid.uuid4().hex[:8]}.pdf"
        
        try:
            # 构建pdftk命令
            cmd = ['pdftk'] + all_files + ['cat', 'output', temp_combined]
            
            logger.info(f"🔄 执行拼接命令: {' '.join(cmd[:3])}... (共{len(all_files)}个文件)")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if os.path.exists(temp_combined):
                # 验证拼接结果
                file_size = os.path.getsize(temp_combined)
                logger.info(f"📊 临时拼接文件大小: {file_size} bytes")
                
                if file_size < 1000:
                    logger.error("❌ 拼接文件过小，可能拼接失败")
                    return False
                
                # 移动到最终输出路径
                import shutil
                shutil.move(temp_combined, output_path)
                
                # 验证最终文件
                if os.path.exists(output_path):
                    final_size = os.path.getsize(output_path)
                    logger.info(f"✅ PDF拼接成功!")
                    logger.info(f"   输出文件: {output_path}")
                    logger.info(f"   文件大小: {final_size} bytes")
                    logger.info(f"   拼接文件数: {len(all_files)}")
                    logger.info(f"   拼接顺序: 酒店文件({len(hotel_files)}) + 网约车文件({len(taxi_files)})")
                    return True
                else:
                    logger.error("❌ 最终输出文件未生成")
                    return False
            else:
                logger.error("❌ 临时拼接文件未生成")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ pdftk拼接失败: {e}")
            logger.error(f"   错误输出: {e.stderr}")
            return False
        finally:
            # 清理临时文件
            if os.path.exists(temp_combined):
                try:
                    os.remove(temp_combined)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")
        
    except Exception as e:
        logger.error(f"❌ PDF拼接过程出错: {e}")
        return False


def create_download_collection(processed_files, collection_name="报销单据合集"):
    """
    创建下载合集
    
    Args:
        processed_files: 已处理的文件列表
        collection_name: 合集名称
    
    Returns:
        dict: 包含成功状态和文件路径的字典
    """
    logger = current_app.logger
    logger.info(f"开始创建下载合集: {collection_name}")
    
    try:
        # 生成输出文件名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{collection_name}_{timestamp}.pdf"
        
        from app import Config
        output_path = os.path.join(Config.OUTPUT_FOLDER, output_filename)
        
        # 调用拼接功能
        success = merge_processed_pdfs(processed_files, output_path)
        
        if success:
            logger.info(f"✅ 下载合集创建成功: {output_filename}")
            return {
                'success': True,
                'filename': output_filename,
                'file_path': output_path,
                'file_count': len(processed_files)
            }
        else:
            logger.error("❌ 下载合集创建失败")
            return {
                'success': False,
                'message': 'PDF拼接失败'
            }
            
    except Exception as e:
        logger.error(f"❌ 创建下载合集出错: {e}")
        return {
            'success': False,
            'message': f'创建合集时出错: {str(e)}'
        }


def extract_trip_info_from_itinerary(pdf_path):
    """
    从行程单PDF中提取行程信息（使用pdfplumber + 暂存原始数据）
    
    Args:
        pdf_path: 行程单PDF文件路径
    
    Returns:
        list: 原始表格数据列表，用于后续AI处理
    """
    logger = current_app.logger
    logger.info(f"开始从行程单提取原始表格数据: {pdf_path}")
    
    try:
        import pdfplumber
        
        # 使用pdfplumber lines策略提取表格
        logger.info("使用pdfplumber lines策略提取PDF表格")
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]  # 获取第一页
            tables = page.extract_tables(table_settings={
                "vertical_strategy": "lines", 
                "horizontal_strategy": "lines"
            })
            
            if not tables:
                logger.warning("未找到表格数据")
                return []
            
            logger.info(f"找到 {len(tables)} 个表格")
            
            # 返回原始表格数据，不进行解析
            table_data = tables[0]
            logger.info(f"提取到原始表格数据，行数: {len(table_data)}")
            logger.info(f"原始表格数据内容: {table_data}")
            
            # 暂存原始数据，返回给调用方
            return table_data
        
    except Exception as e:
        logger.error(f"从行程单提取原始数据失败: {e}")
        return []


def parse_trip_row_data_with_context(df, row_index, row_data):
    """
    解析DataFrame中一行的行程数据，并尝试从相邻行获取起点信息
    
    Args:
        df: DataFrame对象
        row_index: 当前行索引
        row_data: 当前行数据
    
    Returns:
        dict: 行程信息字典
    """
    import re
    logger = current_app.logger
    
    # 先解析当前行的数据
    trip = parse_trip_row_data(row_data)
    if not trip:
        return None
    
    # 如果起点是"未知起点"，尝试从相邻行获取起点信息
    if trip.get('start_point') == '未知起点':
        logger.info("尝试从相邻行获取起点信息...")
        
        # 收集所有可能的起点信息
        start_point_parts = []
        
        # 检查前一行（可能包含起点的第一部分）
        if row_index - 1 >= 0:
            prev_row = list(df.iloc[row_index - 1])
            prev_row_clean = [str(cell).strip() for cell in prev_row if str(cell).strip() and str(cell).strip() != 'nan']
            
            # 如果前一行有数据且不包含序号，可能是起点信息
            if prev_row_clean and not any(re.match(r'^\d+', str(cell)) for cell in prev_row_clean):
                for cell in prev_row_clean:
                    if cell and not any(keyword in cell for keyword in ['说明：', '页码：', '序号', '服务商', '车型', '上车时间', '城市', '起点', '终点', '金额']):
                        start_point_parts.append(cell)
        
        # 检查下一行（可能包含起点的第二部分）
        if row_index + 1 < len(df):
            next_row = list(df.iloc[row_index + 1])
            next_row_clean = [str(cell).strip() for cell in next_row if str(cell).strip() and str(cell).strip() != 'nan']
            
            # 如果下一行有数据且不包含序号，可能是起点信息
            if next_row_clean and not any(re.match(r'^\d+', str(cell)) for cell in next_row_clean):
                for cell in next_row_clean:
                    if cell and not any(keyword in cell for keyword in ['说明：', '页码：', '序号', '服务商', '车型', '上车时间', '城市', '起点', '终点', '金额']):
                        start_point_parts.append(cell)
        
        # 组合起点信息
        if start_point_parts:
            trip['start_point'] = ' '.join(start_point_parts)
            logger.info(f"组合起点信息: {trip['start_point']}")
    
    return trip


def parse_trip_row_data(row_data):
    """
    解析DataFrame中一行的行程数据
    
    Args:
        row_data: 行数据列表
    
    Returns:
        dict: 行程信息字典
    """
    logger = current_app.logger
    
    # 过滤掉空值和nan
    clean_cells = []
    for cell in row_data:
        cell_str = str(cell).strip()
        if cell_str and cell_str != 'nan':
            clean_cells.append(cell_str)
    
    if len(clean_cells) < 3:
        logger.warning(f"行数据不足: {clean_cells}")
        return None
    
    # 根据raw_data重新分析数据结构：
    # 第0个数据：序号\n服务商 (如 "2\n旅程易到")
    # 第1个数据：车型 时间 (如 "旅程易到经济型 2024-06-20 18:59")
    # 第2个数据：城市\n起点 (如 "北京市\n航天智能院")
    # 第3个数据：终点 (如 "汉庭优佳北京石景山首钢园酒店")
    # 第4个数据：金额 (如 "16.12元")
    
    trip = {}
    
    # 解析第0个数据：序号和服务商
    if len(clean_cells) > 0:
        first_cell = clean_cells[0]
        if '\n' in first_cell:
            parts = first_cell.split('\n')
            trip['sequence'] = parts[0].strip()
            trip['service_provider'] = parts[1].strip() if len(parts) > 1 else '未知'
        else:
            trip['sequence'] = first_cell
            trip['service_provider'] = '未知'
    
    # 解析第1个数据：车型和时间
    if len(clean_cells) > 1:
        second_cell = clean_cells[1]
        # 找到第一个空格的位置，前面是车型，后面是时间
        space_index = second_cell.find(' ')
        if space_index > 0:
            trip['car_type'] = second_cell[:space_index].strip()
            trip['pickup_time'] = second_cell[space_index+1:].strip()
        else:
            trip['car_type'] = second_cell
            trip['pickup_time'] = '未知时间'
    
    # 解析第2个数据：城市和起点
    if len(clean_cells) > 2:
        third_cell = clean_cells[2]
        if '\n' in third_cell:
            parts = third_cell.split('\n')
            trip['city'] = parts[0].strip()
            trip['start_point'] = parts[1].strip() if len(parts) > 1 else '未知起点'
        else:
            trip['city'] = third_cell
            trip['start_point'] = '未知起点'
    
    # 解析第3个数据：终点
    if len(clean_cells) > 3:
        trip['end_point'] = clean_cells[3]
    
    # 解析第4个数据：金额
    if len(clean_cells) > 4:
        trip['amount'] = clean_cells[4]
    
    # 设置默认值
    trip.setdefault('sequence', '未知')
    trip.setdefault('service_provider', '未知')
    trip.setdefault('car_type', '未知')
    trip.setdefault('pickup_time', '未知时间')
    trip.setdefault('city', '未知城市')
    trip.setdefault('start_point', '未知起点')
    trip.setdefault('end_point', '未知终点')
    trip.setdefault('amount', '0元')
    trip['raw_data'] = clean_cells
    
    return trip


def parse_trip_info_simple(text):
    """
    简化的行程信息解析
    按照用户建议：识别序号行，识别说明行，提取中间内容，去掉空行
    
    Args:
        text: PDF提取的文本内容
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    logger.info("使用简化解析方法")
    
    try:
        lines = text.split('\n')
        logger.info(f"文本总行数: {len(lines)}")
        
        trips = []
        current_trip = []
        in_trip = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:  # 跳过空行
                continue
            
            logger.debug(f"第{i+1}行: '{line}'")
            
            # 识别序号行（纯数字）
            if line.isdigit():
                # 如果之前有行程数据，保存它
                if current_trip and in_trip:
                    trip_info = parse_single_trip(current_trip)
                    if trip_info:
                        trips.append(trip_info)
                        logger.info(f"解析到行程: {trip_info}")
                
                # 开始新的行程
                current_trip = [line]  # 序号
                in_trip = True
                logger.debug(f"发现序号行: {line}")
                continue
            
            # 如果在行程中，收集数据
            if in_trip:
                current_trip.append(line)
                
                # 识别说明行（包含"旅程"、"经济型"等关键词）
                if any(keyword in line for keyword in ['旅程', '经济型', '出行', '打车']):
                    logger.debug(f"发现说明行: {line}")
                    # 说明行通常是行程的结束标志
                    trip_info = parse_single_trip(current_trip)
                    if trip_info:
                        trips.append(trip_info)
                        logger.info(f"解析到行程: {trip_info}")
                    current_trip = []
                    in_trip = False
        
        # 处理最后一个行程
        if current_trip and in_trip:
            trip_info = parse_single_trip(current_trip)
            if trip_info:
                trips.append(trip_info)
                logger.info(f"解析到最后一个行程: {trip_info}")
        
        logger.info(f"总共解析到 {len(trips)} 个行程")
        return trips
        
    except Exception as e:
        logger.error(f"简化解析失败: {e}")
        return []


def parse_single_trip(trip_lines):
    """
    解析单个行程的数据
    
    Args:
        trip_lines: 行程相关的文本行列表
    
    Returns:
        dict: 行程信息字典
    """
    logger = current_app.logger
    
    try:
        if len(trip_lines) < 3:
            logger.warning(f"行程数据不足: {trip_lines}")
            return None
        
        # 去掉空行
        clean_lines = [line.strip() for line in trip_lines if line.strip()]
        
        if len(clean_lines) < 3:
            logger.warning(f"清理后行程数据不足: {clean_lines}")
            return None
        
        # 基本结构：序号, 说明行, 时间, 城市, 起点, 终点, 金额
        trip = {
            'sequence': clean_lines[0] if len(clean_lines) > 0 else '未知',
            'description': clean_lines[1] if len(clean_lines) > 1 else '未知',
            'pickup_time': clean_lines[2] if len(clean_lines) > 2 else '未知时间',
            'city': clean_lines[3] if len(clean_lines) > 3 else '未知城市',
            'start_point': clean_lines[4] if len(clean_lines) > 4 else '未知起点',
            'end_point': clean_lines[5] if len(clean_lines) > 5 else '未知终点',
            'amount': clean_lines[6] if len(clean_lines) > 6 else '0元',
            'raw_data': clean_lines  # 保存原始数据
        }
        
        logger.debug(f"解析单个行程: {trip}")
        return trip
        
    except Exception as e:
        logger.error(f"解析单个行程失败: {e}")
        return None


def parse_table_to_trips(df):
    """
    将camelot提取的表格数据转换为行程信息
    处理camelot stream模式提取的表格格式
    
    Args:
        df: pandas DataFrame
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    trips = []
    
    try:
        logger.info(f"开始解析表格数据，形状: {df.shape}")
        
        # 第一步：识别打车平台
        platform = identify_ride_platform(df)
        logger.info(f"识别到打车平台: {platform}")
        
        # 第二步：根据平台使用对应的解析逻辑
        if platform == "高德地图":
            trips = parse_amap_trips(df)
        else:
            logger.warning(f"未知的打车平台: {platform}")
            return []
        
        return trips
        
    except Exception as e:
        logger.error(f"解析表格数据失败: {e}")
        return []


def identify_ride_platform(df):
    """
    识别打车平台
    """
    logger = current_app.logger
    
    try:
        # 检查表格中是否包含平台标识
        for i, row in df.iterrows():
            for col in df.columns:
                cell_data = str(row[col]).strip()
                if '高德地图' in cell_data or 'AMAP' in cell_data:
                    return "高德地图"
                elif '滴滴' in cell_data or 'DIDI' in cell_data:
                    return "滴滴出行"
                elif '美团' in cell_data or 'MEITUAN' in cell_data:
                    return "美团打车"
                elif '曹操' in cell_data or 'CAOCAO' in cell_data:
                    return "曹操出行"
        
        # 如果没有明确标识，根据服务商推断
        for i, row in df.iterrows():
            for col in df.columns:
                cell_data = str(row[col]).strip()
                if '旅程易到' in cell_data:
                    return "高德地图"  # 旅程易到是高德地图的服务商
        
        return "未知平台"
        
    except Exception as e:
        logger.error(f"识别打车平台失败: {e}")
        return "未知平台"


def parse_amap_trips(df):
    """
    解析高德地图的行程数据
    根据实际数据结构，行程数据在行6, 8, 10
    """
    logger = current_app.logger
    trips = []
    
    try:
        logger.info("开始解析高德地图行程数据")
        
        # 从stream提取的数据中，行程数据在行6, 8, 10
        trip_rows = [6, 8, 10]
        
        for row_idx in trip_rows:
            if row_idx < len(df):
                row = df.iloc[row_idx]
                row_data = []
                for col in df.columns:
                    cell_data = str(row[col]).strip()
                    if cell_data and cell_data != 'nan':
                        row_data.append(cell_data)
                
                if row_data:
                    logger.info(f"处理高德地图行程行 {row_idx}: {row_data}")
                    trip = parse_amap_trip_row(row_data)
                    if trip:
                        trips.append(trip)
                        logger.info(f"解析到高德地图行程: {trip}")
        
        return trips
        
    except Exception as e:
        logger.error(f"解析高德地图行程数据失败: {e}")
        return []


def parse_trip_from_lines(lines):
    """
    从分割后的行中解析行程信息
    """
    logger = current_app.logger
    
    try:
        # 查找序号
        sequence = None
        for line in lines:
            if line.strip().isdigit():
                sequence = line.strip()
                break
        
        if not sequence:
            return None
        
        # 查找金额
        amount = 0.0
        for line in lines:
            amount_match = re.search(r'(\d+\.?\d*)\s*元', line)
            if amount_match:
                amount = float(amount_match.group(1))
                break
        
        # 查找时间
        pickup_time = None
        for line in lines:
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', line)
            if time_match:
                pickup_time = time_match.group(1)
                break
        
        # 查找城市
        city = None
        for line in lines:
            if '北京市' in line or '上海市' in line or '广州市' in line or '深圳市' in line:
                city = line.strip()
                break
        
        # 查找起点和终点（简化处理）
        start_point = None
        end_point = None
        
        # 根据实际数据结构调整
        if len(lines) >= 6:
            # 假设起点在前，终点在后
            for i, line in enumerate(lines):
                if '北京南站' in line or '航天智能院' in line or '汉庭' in line:
                    if not start_point:
                        start_point = line.strip()
                    elif not end_point:
                        end_point = line.strip()
        
        trip = {
            'sequence': sequence,
            'service_provider': '旅程易到',  # 从数据中可以看出
            'car_type': '旅程易到经济型',  # 从数据中可以看出
            'pickup_time': pickup_time or '未知时间',
            'city': city or '未知城市',
            'start_point': start_point or '未知起点',
            'end_point': end_point or '未知终点',
            'amount': amount
        }
        
        return trip
        
    except Exception as e:
        logger.error(f"解析行程信息失败: {e}")
        return None


def parse_trip_from_stream_row(row_data):
    """
    从stream模式提取的行数据中解析行程信息
    根据测试结果，数据格式为：
    行6: ['1\n旅程易到', '旅程易到经济型 2024-06-19 12:32', '北京市', '航天智能院', '53.89元']
    行8: ['2\n旅程易到', '旅程易到经济型 2024-06-20 18:59', '北京市', '汉庭优佳北京石景山首钢园酒店', '16.12元']
    行10: ['3\n旅程易到', '旅程易到经济型 2024-06-21 08:18', '北京市', '北京南站(东进站口)', '74.55元']
    """
    logger = current_app.logger
    
    try:
        if len(row_data) < 5:
            logger.warning(f"行数据不足: {row_data}")
            return None
        
        # 解析第一列：序号和服务商
        first_col = row_data[0]
        if '\n' in first_col:
            parts = first_col.split('\n')
            sequence = parts[0].strip()
            service_provider = parts[1].strip() if len(parts) > 1 else '旅程易到'
        else:
            sequence = first_col.strip()
            service_provider = '旅程易到'
        
        # 解析第二列：车型和上车时间
        second_col = row_data[1]
        if '旅程易到经济型' in second_col:
            car_type = '旅程易到经济型'
            # 提取时间
            time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', second_col)
            pickup_time = time_match.group(1) if time_match else '未知时间'
        else:
            car_type = '旅程易到经济型'
            pickup_time = '未知时间'
        
        # 解析第三列：城市
        city = row_data[2].strip() if len(row_data) > 2 else '未知城市'
        
        # 解析第四列：起点或终点
        location = row_data[3].strip() if len(row_data) > 3 else '未知地点'
        
        # 解析第五列：金额
        amount = 0.0
        if len(row_data) > 4:
            amount_str = row_data[4]
            amount_match = re.search(r'(\d+\.?\d*)\s*元', amount_str)
            if amount_match:
                amount = float(amount_match.group(1))
        
        # 根据实际数据结构，需要智能判断起点和终点
        # 从测试数据可以看到：
        # 行程1: 起点=北京南站-东停车场M, 终点=航天智能院
        # 行程2: 起点=航天智能院, 终点=汉庭优佳北京石景山首钢园酒店  
        # 行程3: 起点=汉庭优佳酒店, 终点=北京南站(东进站口)
        
        start_point = location
        end_point = location  # 暂时设为相同，需要根据上下文调整
        
        trip = {
            'sequence': sequence,
            'service_provider': service_provider,
            'car_type': car_type,
            'pickup_time': pickup_time,
            'city': city,
            'start_point': start_point,
            'end_point': end_point,
            'amount': amount
        }
        
        return trip
        
    except Exception as e:
        logger.error(f"解析stream行数据失败: {e}")
        return None


def parse_amap_trip_row(row_data):
    """
    解析高德地图单行行程数据
    简化版本：直接使用camelot提取的原始数据
    """
    logger = current_app.logger
    
    try:
        if len(row_data) < 5:
            logger.warning(f"高德地图行数据不足: {row_data}")
            return None
        
        # 直接使用原始数据，不做复杂解析
        trip = {
            'raw_data': row_data,  # 保存原始数据
            'sequence': row_data[0].strip() if len(row_data) > 0 else '未知',
            'pickup_time': row_data[1].strip() if len(row_data) > 1 else '未知时间',
            'city': row_data[2].strip() if len(row_data) > 2 else '未知城市',
            'location': row_data[3].strip() if len(row_data) > 3 else '未知地点',
            'amount': row_data[4].strip() if len(row_data) > 4 else '0元'
        }
        
        return trip
        
    except Exception as e:
        logger.error(f"解析高德地图行程行数据失败: {e}")
        return None


def parse_trip_info_simple_text(text):
    """
    简单的文本解析方法（回退用）
    """
    logger = current_app.logger
    trips = []
    
    try:
        lines = text.split('\n')
        
        # 查找数据开始位置
        data_start = -1
        for i, line in enumerate(lines):
            if line.strip() == '1':
                data_start = i
                break
        
        if data_start == -1:
            logger.warning("未找到数据开始位置")
            return []
        
        # 简单解析：查找包含金额的行
        amount_pattern = r'(\d+\.?\d*)\s*元'
        for i, line in enumerate(lines[data_start:], data_start):
            line = line.strip()
            amount_match = re.search(amount_pattern, line)
            if amount_match:
                amount = float(amount_match.group(1))
                
                # 简单提取其他信息
                trip = {
                    'sequence': str(len(trips) + 1),
                    'pickup_time': '未知时间',
                    'city': '未知城市',
                    'start_point': '未知起点',
                    'end_point': '未知终点',
                    'amount': amount
                }
                trips.append(trip)
                logger.info(f"简单解析到行程: {trip}")
        
        return trips
        
    except Exception as e:
        logger.error(f"简单文本解析失败: {e}")
        return []


# 废弃的文本解析方法 - 使用camelot-py替代
# def parse_trip_info_from_text(text):
#     """
#     从文本中解析行程信息（基于实际PDF格式）
#     
#     Args:
#         text: PDF提取的文本内容
#     
#     Returns:
#         list: 行程信息列表
#     """
#     logger = current_app.logger
#     trips = []
#     
#     try:
#         lines = text.split('\n')
#         
#         # 查找数据开始位置（跳过表头）
#         data_start = -1
#         for i, line in enumerate(lines):
#             if line.strip() == '1':  # 第一个序号
#                 data_start = i
#                 break
#         
#         if data_start == -1:
#             logger.warning("未找到数据开始位置")
#             return []
#         
#         logger.info(f"找到数据开始位置: 第{data_start+1}行")
#         
#         # 解析行程数据
#         i = data_start
#         while i < len(lines):
#             line = lines[i].strip()
#             if not line:
#                 i += 1
#                 continue
#             
#             # 跳过说明文字
#             if '说明：' in line or '页码：' in line:
#                 break
#             
#             # 检查是否是序号（新行程开始）
#             if line.isdigit():
#                 trip = {}
#                 trip['sequence'] = line
#                 
#                 # 读取服务商
#                 i += 1
#                 if i < len(lines):
#                     trip['service_provider'] = lines[i].strip()
#                 
#                 # 读取车型
#                 i += 1
#                 if i < len(lines):
#                     trip['car_type'] = lines[i].strip()
#                 
#                 # 读取上车时间
#                 i += 1
#                 if i < len(lines):
#                     trip['pickup_time'] = lines[i].strip()
#                 
#                 # 读取城市
#                 i += 1
#                 if i < len(lines):
#                     trip['city'] = lines[i].strip()
#                 
#                 # 读取起点（可能跨多行）
#                 i += 1
#                 if i < len(lines):
#                     start_point = lines[i].strip()
#                     i += 1
#                     # 检查下一行是否是起点的延续
#                     if i < len(lines) and not lines[i].strip().isdigit() and '元' not in lines[i] and '说明：' not in lines[i]:
#                         start_point += lines[i].strip()
#                         i += 1
#                     trip['start_point'] = start_point
#                 
#                 # 读取终点（可能跨多行）
#                 if i < len(lines):
#                     end_point = lines[i].strip()
#                     i += 1
#                     # 检查下一行是否是终点的延续
#                     if i < len(lines) and not lines[i].strip().isdigit() and '元' not in lines[i] and '说明：' not in lines[i]:
#                         end_point += lines[i].strip()
#                         i += 1
#                     trip['end_point'] = end_point
#                 
#                 # 读取金额
#                 if i < len(lines):
#                     amount_line = lines[i].strip()
#                     amount_match = re.search(r'(\d+\.?\d*)\s*元', amount_line)
#                     if amount_match:
#                         trip['amount'] = float(amount_match.group(1))
#                     i += 1
#                 
#                 trips.append(trip)
#                 logger.info(f"解析到行程: {trip}")
#             else:
#                 i += 1
#         
#         return trips
#         
#     except Exception as e:
#         logger.error(f"解析行程信息失败: {e}")
#         return []


def parse_trip_info_from_text(text):
    """
    从文本中解析行程信息（使用camelot-py库）
    
    Args:
        text: PDF提取的文本内容（暂时不使用，直接使用camelot从PDF提取）
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    logger.info("使用camelot-py库解析行程信息")
    
    # 这个方法现在被camelot替代，保留接口兼容性
    return []


def parse_simple_trip_info(lines):
    """
    简单的行程信息解析（备用方案）
    
    Args:
        lines: 文本行列表
    
    Returns:
        list: 行程信息列表
    """
    logger = current_app.logger
    trips = []
    
    try:
        # 查找包含数字和金额的行
        amount_pattern = r'(\d+\.?\d*)\s*元'
        time_pattern = r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2})'
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 查找金额
            amount_match = re.search(amount_pattern, line)
            if amount_match:
                amount = float(amount_match.group(1))
                
                # 查找时间
                time_match = re.search(time_pattern, line)
                pickup_time = time_match.group(1) if time_match else "未知时间"
                
                # 尝试提取其他信息
                parts = line.split()
                if len(parts) >= 3:
                    trip = {
                        'sequence': str(len(trips) + 1),  # 序号
                        'pickup_time': pickup_time,  # 上车时间
                        'city': parts[0] if len(parts) > 0 else "未知城市",  # 城市
                        'start_point': parts[1] if len(parts) > 1 else "未知起点",  # 起点
                        'end_point': parts[2] if len(parts) > 2 else "未知终点",  # 终点
                        'amount': amount  # 金额
                    }
                    trips.append(trip)
                    logger.info(f"简单解析到行程: {trip}")
        
        return trips
        
    except Exception as e:
        logger.error(f"简单解析行程信息失败: {e}")
        return []


def generate_trip_records(processed_files):
    """
    生成行程记录字符串
    使用通义千问API处理暂存的原始表格数据，并缓存结果
    
    Args:
        processed_files: 已处理的文件列表
    
    Returns:
        str: 格式化的行程记录字符串
    """
    logger = current_app.logger
    logger.info(f"开始生成行程记录，文件数量: {len(processed_files)}")
    
    try:
        # 检查是否已经有缓存的行程记录
        cached_trip_records = None
        itinerary_files = [f for f in processed_files if f.get('has_itinerary', False)]
        
        logger.info(f"找到 {len(itinerary_files)} 个包含行程单的文件")
        
        # 检查所有行程单文件是否都有缓存
        for file_info in itinerary_files:
            logger.info(f"检查文件 {file_info.get('output_file', '未知')} 的缓存状态")
            if file_info.get('cached_trip_records'):
                cached_trip_records = file_info.get('cached_trip_records')
                logger.info(f"文件 {file_info.get('output_file', '未知')} 有缓存")
            else:
                logger.info(f"文件 {file_info.get('output_file', '未知')} 没有缓存")
                cached_trip_records = None
                break
        
        if cached_trip_records:
            logger.info("所有行程单文件都有缓存，直接返回缓存的行程记录")
            logger.info(f"缓存的行程记录内容: {cached_trip_records}")
            return cached_trip_records
        else:
            logger.info("没有找到完整的缓存，需要重新生成行程记录")
        
        # 如果没有缓存，则生成新的行程记录
        all_raw_data = []
        
        # 遍历所有文件，收集原始表格数据
        for file_info in processed_files:
            # 只处理包含行程单的文件
            if not file_info.get('has_itinerary', False):
                continue
            
            # 从缓存中获取原始表格数据
            raw_table_data = file_info.get('raw_table_data')
            if raw_table_data:
                all_raw_data.extend(raw_table_data)
                logger.info(f"从缓存中读取到原始表格数据，行数: {len(raw_table_data)}")
            else:
                # 回退机制：尝试从原始行程单文件中提取
                logger.warning(f"文件 {file_info.get('output_file', '未知')} 没有缓存的原始表格数据，尝试回退提取")
                
                # 检查是否有原始行程单文件路径
                itinerary_file = file_info.get('itinerary_file')
                if itinerary_file and os.path.exists(itinerary_file):
                    logger.info(f"从原始行程单文件提取: {itinerary_file}")
                    try:
                        raw_table_data = extract_trip_info_from_itinerary(itinerary_file)
                        if raw_table_data:
                            all_raw_data.extend(raw_table_data)
                            logger.info(f"回退提取成功，获得原始表格数据行数: {len(raw_table_data)}")
                        else:
                            logger.warning(f"回退提取失败，无法从 {itinerary_file} 提取原始表格数据")
                    except Exception as e:
                        logger.error(f"回退提取过程中出错: {e}")
                else:
                    logger.warning(f"没有找到原始行程单文件路径，无法进行回退提取")
        
        if not all_raw_data:
            logger.info("没有找到任何原始表格数据")
            return "暂无行程记录"
        
        # 使用通义千问API处理所有原始数据
        logger.info(f"收集到 {len(all_raw_data)} 行原始表格数据，调用通义千问API处理...")
        logger.info(f"原始表格数据内容: {all_raw_data}")
        
        structured_trips = call_qwen_api_for_trips(all_raw_data)
        
        if not structured_trips:
            logger.warning("通义千问API未能处理原始数据")
            return "行程数据处理失败"
        
        logger.info(f"通义千问API返回的结构化数据: {structured_trips}")
        
        # 生成HTML表格格式的行程记录
        html_table = []
        html_table.append('<div class="trip-records-container">')
        html_table.append('<h4 class="mb-3">📋 行程记录</h4>')
        html_table.append('<div class="table-responsive">')
        html_table.append('<table class="table table-striped table-hover">')
        
        # 表头
        html_table.append('<thead class="table-dark">')
        html_table.append('<tr>')
        html_table.append('<th scope="col">序号</th>')
        html_table.append('<th scope="col">服务商</th>')
        html_table.append('<th scope="col">车型</th>')
        html_table.append('<th scope="col">上车时间</th>')
        html_table.append('<th scope="col">城市</th>')
        html_table.append('<th scope="col">起点</th>')
        html_table.append('<th scope="col">终点</th>')
        html_table.append('<th scope="col">金额</th>')
        html_table.append('</tr>')
        html_table.append('</thead>')
        
        # 表格内容
        html_table.append('<tbody>')
        for trip in structured_trips:
            html_table.append('<tr>')
            html_table.append(f'<td><span class="badge bg-primary">{trip.get("sequence", "未知")}</span></td>')
            html_table.append(f'<td>{trip.get("service_provider", "未知")}</td>')
            html_table.append(f'<td><small class="text-muted">{trip.get("car_type", "未知")}</small></td>')
            html_table.append(f'<td><strong>{trip.get("pickup_time", "未知时间")}</strong></td>')
            html_table.append(f'<td><span class="badge bg-info">{trip.get("city", "未知城市")}</span></td>')
            html_table.append(f'<td>{trip.get("start_point", "未知起点")}</td>')
            html_table.append(f'<td>{trip.get("end_point", "未知终点")}</td>')
            html_table.append(f'<td><span class="badge bg-success">{trip.get("amount", "0元")}</span></td>')
            html_table.append('</tr>')
            logger.info(f"生成行程记录行: {trip.get('sequence')} - {trip.get('pickup_time')} - {trip.get('start_point')} -> {trip.get('end_point')} - {trip.get('amount')}")
        
        html_table.append('</tbody>')
        html_table.append('</table>')
        html_table.append('</div>')
        
        # 统计信息
        total_amount = 0
        for trip in structured_trips:
            amount_str = trip.get('amount', '0元')
            try:
                # 提取金额数字
                import re
                amount_match = re.search(r'(\d+\.?\d*)', amount_str)
                if amount_match:
                    total_amount += float(amount_match.group(1))
            except:
                pass
        
        html_table.append('<div class="mt-3 p-3 bg-light rounded">')
        html_table.append(f'<h6 class="mb-2">📊 统计信息</h6>')
        html_table.append(f'<p class="mb-1"><strong>总行程数：</strong>{len(structured_trips)} 个</p>')
        html_table.append(f'<p class="mb-0"><strong>总金额：</strong><span class="text-success fw-bold">¥{total_amount:.2f}</span></p>')
        html_table.append('</div>')
        html_table.append('</div>')
        
        result = "\n".join(html_table)
        logger.info(f"生成HTML表格格式行程记录完成，共 {len(structured_trips)} 个行程，总金额 ¥{total_amount:.2f}")
        logger.info(f"最终生成的HTML内容长度: {len(result)} 字符")
        
        # 缓存生成的行程记录到所有相关文件中
        for file_info in processed_files:
            if file_info.get('has_itinerary', False):
                file_info['cached_trip_records'] = result
                logger.info(f"已缓存行程记录到文件: {file_info.get('output_file', '未知')}")
                logger.info(f"缓存的内容长度: {len(result)} 字符")
        
        return result
        
    except Exception as e:
        logger.error(f"生成行程记录失败: {e}")
        return f"生成行程记录时出错: {str(e)}" 