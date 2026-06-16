#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滴滴出行 PDF 行程单解析器

参考高德实现（trip_table_parse_enhanced.py），使用 pdfplumber 提取表格，
返回与高德解析器一致的 JSON 结构，供「查看行程」等功能复用。
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import pymupdf
except ImportError:
    pymupdf = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


_DIDI_HEADER_ALIASES = {
    '序号': '序号',
    '车型': '车型',
    '上车时间': '上车时间',
    '城市': '城市',
    '起点': '起点',
    '终点': '终点',
    '里程[公里]': '里程',
    '金额[元]': '金额',
    '备注': '备注',
}


def is_didi_itinerary(pdf_path: str) -> bool:
    """判断是否为滴滴出行行程单。"""
    if not pymupdf:
        return False
    doc = None
    try:
        doc = pymupdf.open(pdf_path)
        text = doc[0].get_text()
        return (
            '滴滴出行' in text
            or 'DIDI TRAVEL' in text
            or 'didi travel' in text.lower()
        )
    except Exception as e:
        logger.warning(f"判断滴滴行程单失败: {e}")
        return False
    finally:
        if doc:
            doc.close()


def _extract_basic_text(pdf_path: str) -> str:
    if not pymupdf:
        return ''
    doc = None
    try:
        doc = pymupdf.open(pdf_path)
        return doc[0].get_text()
    finally:
        if doc:
            doc.close()


def _parse_date_range(basic_text: str) -> tuple:
    """从「行程起止日期」提取起止日期，用于补全上车时间年份。"""
    match = re.search(
        r'行程起止日期[：:]\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})',
        basic_text,
    )
    if match:
        return match.group(1), match.group(2)
    match = re.search(r'申请日期[：:]\s*(\d{4}-\d{2}-\d{2})', basic_text)
    if match:
        d = match.group(1)
        return d, d
    return '', ''


def _normalize_pickup_time(raw_time: str, start_date: str, end_date: str) -> str:
    """
    将「05-30 10:01 周六」补全为「2026-05-30 10:01」。
    若已是完整格式则原样返回。
    """
    raw_time = (raw_time or '').strip()
    if not raw_time:
        return ''

    full_match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', raw_time)
    if full_match:
        return full_match.group(1)

    short_match = re.match(r'(\d{2})-(\d{2})\s+(\d{2}:\d{2})', raw_time)
    if not short_match:
        return raw_time

    month, day, clock = short_match.groups()
    year = ''
    for date_str in (start_date, end_date):
        if date_str and date_str[5:7] == month and date_str[8:10] == day:
            year = date_str[:4]
            break
    if not year:
        for date_str in (start_date, end_date):
            if date_str:
                year = date_str[:4]
                break
    if not year:
        return raw_time

    return f'{year}-{month}-{day} {clock}'


def _header_index(row: List[Any]) -> Dict[str, int]:
    mapping = {}
    for idx, cell in enumerate(row or []):
        name = str(cell or '').strip().replace('\r', ' ').replace('\n', ' ')
        if name in _DIDI_HEADER_ALIASES:
            mapping[_DIDI_HEADER_ALIASES[name]] = idx
    return mapping


def _cell(row: List[Any], idx: Optional[int]) -> str:
    if idx is None or idx >= len(row):
        return ''
    return str(row[idx] or '').strip().replace('\r', ' ').replace('\n', ' ')


def _parse_table_rows(
    table_rows: List[List[Any]],
    start_date: str,
    end_date: str,
) -> List[Dict[str, str]]:
    if not table_rows:
        return []

    header_map = _header_index(table_rows[0])
    data_rows = table_rows[1:] if header_map else table_rows

    # 无表头时按滴滴默认列顺序推断
    if not header_map and data_rows:
        sample = data_rows[0]
        if len(sample) >= 8 and re.match(r'^\d+$', _cell(sample, 0)):
            header_map = {
                '序号': 0,
                '车型': 1,
                '上车时间': 2,
                '城市': 3,
                '起点': 4,
                '终点': 5,
                '金额': 7,
            }

    trips: List[Dict[str, str]] = []
    for row in data_rows:
        seq = _cell(row, header_map.get('序号'))
        if not seq or not re.match(r'^\d+$', seq):
            continue

        amount = _cell(row, header_map.get('金额'))
        if amount and not re.match(r'^\d', amount):
            continue

        pickup_raw = _cell(row, header_map.get('上车时间'))
        trips.append({
            '序号': seq,
            '服务商': '滴滴出行',
            '车型': _cell(row, header_map.get('车型')),
            '上车时间': _normalize_pickup_time(pickup_raw, start_date, end_date),
            '城市': _cell(row, header_map.get('城市')),
            '起点': _cell(row, header_map.get('起点')),
            '终点': _cell(row, header_map.get('终点')),
            '金额(元)': amount,
        })

    return trips


def _extract_tables_with_pdfplumber(pdf_path: str) -> List[List[List[Any]]]:
    if not pdfplumber:
        return []
    tables: List[List[List[Any]]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables() or []
            tables.extend(page_tables)
    return tables


def parse_didi_itinerary_enhanced(pdf_path: str) -> Dict[str, Any]:
    """解析滴滴出行 PDF 行程单。"""
    if not os.path.exists(pdf_path):
        return {'success': False, 'error': f'文件不存在: {pdf_path}'}

    if not is_didi_itinerary(pdf_path):
        return {'success': False, 'error': '不是滴滴出行行程单'}

    try:
        basic_text = _extract_basic_text(pdf_path)
        start_date, end_date = _parse_date_range(basic_text)

        result: Dict[str, Any] = {
            'success': True,
            'platform': '滴滴出行',
            'filename': os.path.basename(pdf_path),
            'basic_info': {},
            'trips': [],
        }

        apply_match = re.search(r'申请日期[：:]\s*(\d{4}-\d{2}-\d{2})', basic_text)
        if apply_match:
            result['basic_info']['apply_time'] = apply_match.group(1)

        phone_match = re.search(r'行程人手机号[：:]\s*(\d{11})', basic_text)
        if phone_match:
            result['basic_info']['phone'] = phone_match.group(1)

        if start_date:
            result['basic_info']['trip_start_time'] = start_date
        if end_date:
            result['basic_info']['trip_end_time'] = end_date

        count_match = re.search(r'共(\d+)笔行程', basic_text)
        if count_match:
            result['basic_info']['trip_count'] = int(count_match.group(1))

        amount_match = re.search(r'合计([\d.]+)元', basic_text)
        if amount_match:
            result['basic_info']['total_amount'] = float(amount_match.group(1))

        all_trips: List[Dict[str, str]] = []
        for table in _extract_tables_with_pdfplumber(pdf_path):
            all_trips.extend(_parse_table_rows(table, start_date, end_date))

        # 去重：多页或重复表格时按序号保留第一条
        seen = set()
        deduped = []
        for trip in all_trips:
            key = (
                trip.get('序号'),
                trip.get('上车时间'),
                trip.get('起点'),
                trip.get('终点'),
                trip.get('金额(元)'),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(trip)

        result['trips'] = deduped
        if not deduped:
            result['warning'] = '未能解析到行程表格数据'
        else:
            logger.info(f'滴滴行程单解析成功: {len(deduped)} 条')

        return result

    except Exception as e:
        logger.error(f'解析滴滴行程单失败: {e}', exc_info=True)
        return {'success': False, 'error': str(e)}


def parse_didi_trips_from_raw_table(
    raw_table_data: List[List[Any]],
    basic_text: str = '',
) -> List[Dict[str, str]]:
    """从 process 阶段缓存的 raw_table_data 还原行程（itinerary_file 不可用时兜底）。"""
    start_date, end_date = _parse_date_range(basic_text)
    return _parse_table_rows(raw_table_data, start_date, end_date)
