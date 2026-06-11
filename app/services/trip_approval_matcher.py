import datetime
import re


DATE_PATTERNS = (
    re.compile(r'(?<!\d)(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)'),
    re.compile(r'(?<!\d)(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日?'),
    re.compile(r'(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)'),
)


def _parse_date(year, month, day):
    try:
        return datetime.date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def extract_dates_from_text(value):
    """Extract normalized dates from arbitrary ticket or approval text."""
    if value is None:
        return []
    text = str(value)
    dates = []
    seen = set()
    for pattern in DATE_PATTERNS:
        for match in pattern.findall(text):
            parsed = _parse_date(*match)
            if parsed and parsed.isoformat() not in seen:
                seen.add(parsed.isoformat())
                dates.append(parsed)
    return dates


def _walk_values(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _walk_values(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from _walk_values(nested)
    else:
        yield value


def _date_range_from_values(values):
    dates = []
    for value in values:
        if isinstance(value, datetime.date):
            dates.append(value)
        else:
            dates.extend(extract_dates_from_text(value))
    if not dates:
        return None
    dates = sorted(set(dates))
    return {
        'start_date': dates[0].isoformat(),
        'end_date': dates[-1].isoformat(),
        'dates': [item.isoformat() for item in dates],
    }


def infer_trip_date_range(processed_files=None, form_values=None):
    """Infer the reimbursement trip date range from form inputs and ticket data."""
    evidence = []
    explicit_values = []
    form_values = form_values or {}
    for key in ('start_date', 'return_date', 'end_date'):
        value = form_values.get(key)
        if value:
            explicit_values.append(value)
            evidence.append({'source': 'form', 'key': key, 'value': str(value)})

    explicit_range = _date_range_from_values(explicit_values)
    if explicit_range:
        explicit_range['source'] = 'form'
        explicit_range['evidence'] = evidence
        return explicit_range

    candidate_values = []
    for file_info in processed_files or []:
        if not isinstance(file_info, dict):
            continue
        for key in (
            'ticket_dates',
            'travel_dates',
            'train_ticket_dates',
            'flight_ticket_dates',
            'pickup_time',
            'order_id',
            'display_name',
        ):
            if file_info.get(key):
                candidate_values.append(file_info.get(key))
                evidence.append({'source': 'processed_file', 'key': key, 'value': str(file_info.get(key))[:120]})
        for item in file_info.get('train_ticket_items') or []:
            if not isinstance(item, dict):
                continue
            for key in ('ticket_dates', 'travel_date', 'departure_time', 'arrival_time', 'source_name', 'display_name'):
                if item.get(key):
                    candidate_values.append(item.get(key))
                    evidence.append({'source': 'ticket_item', 'key': key, 'value': str(item.get(key))[:120]})
        raw_table_data = file_info.get('raw_table_data') or []
        if raw_table_data:
            candidate_values.append(raw_table_data)
            evidence.append({'source': 'raw_table_data', 'key': 'raw_table_data', 'value': '行程表格'})

    inferred = _date_range_from_values(_walk_values(candidate_values))
    if inferred:
        inferred['source'] = 'ticket'
        inferred['evidence'] = evidence[:12]
    return inferred


def _range_to_dates(date_range):
    if not date_range:
        return None
    try:
        return (
            datetime.date.fromisoformat(date_range['start_date']),
            datetime.date.fromisoformat(date_range['end_date']),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _overlap_days(left, right):
    start = max(left[0], right[0])
    end = min(left[1], right[1])
    return max((end - start).days + 1, 0)


def _distance_days(left, right):
    if left[1] < right[0]:
        return (right[0] - left[1]).days
    if right[1] < left[0]:
        return (left[0] - right[1]).days
    return 0


def _approval_date_range(approval):
    values = [
        approval.get('title'),
        approval.get('create_time'),
        approval.get('finish_time'),
        approval.get('business_id'),
    ]
    for field in approval.get('fields') or []:
        values.append(field.get('name'))
        values.append(field.get('value'))
    return _date_range_from_values(values)


def rank_related_approvals(approvals, processed_files=None, form_values=None):
    inferred_range = infer_trip_date_range(processed_files, form_values)
    inferred_dates = _range_to_dates(inferred_range)
    ranked = []
    for approval in approvals or []:
        item = dict(approval)
        approval_range = _approval_date_range(item)
        approval_dates = _range_to_dates(approval_range)
        score = 0
        reason = '暂无票据日期，按最近审批排序'

        if inferred_dates and approval_dates:
            overlap = _overlap_days(inferred_dates, approval_dates)
            distance = _distance_days(inferred_dates, approval_dates)
            if overlap > 0:
                score = 100 + overlap
                reason = f'行程日期重叠 {overlap} 天'
            else:
                score = max(1, 80 - min(distance, 80))
                reason = f'行程日期相差 {distance} 天'
        elif approval_dates:
            score = 10
            reason = '审批单包含行程日期'

        title = str(item.get('title') or '')
        if '出差' in title:
            score += 5
        if str(item.get('status') or '').upper() in {'COMPLETED', 'RUNNING'}:
            score += 2

        item['match_score'] = score
        item['match_reason'] = reason
        item['approval_date_range'] = approval_range
        ranked.append(item)

    ranked.sort(key=lambda item: (item.get('match_score') or 0, item.get('create_time') or ''), reverse=True)
    for index, item in enumerate(ranked, start=1):
        item['match_rank'] = index
        item['recommended'] = index == 1 and (item.get('match_score') or 0) >= 60
    return ranked, inferred_range
