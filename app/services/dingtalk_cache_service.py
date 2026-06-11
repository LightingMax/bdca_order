import json
import os
import sqlite3
from datetime import datetime


def _connect(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA busy_timeout=3000')
    return connection


def _ensure_schema(connection):
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS dingtalk_related_approval_cache (
            cache_key TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            process_code TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            statuses_json TEXT NOT NULL,
            limit_count INTEGER NOT NULL,
            approvals_json TEXT NOT NULL,
            cached_at TEXT NOT NULL
        )
        '''
    )
    connection.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_dingtalk_related_approval_cache_user
        ON dingtalk_related_approval_cache(user_id, process_code)
        '''
    )
    connection.commit()


def get_related_approval_cache(db_path, cache_key):
    with _connect(db_path) as connection:
        _ensure_schema(connection)
        row = connection.execute(
            '''
            SELECT approvals_json, cached_at
            FROM dingtalk_related_approval_cache
            WHERE cache_key = ?
            ''',
            (cache_key,),
        ).fetchone()
    if not row:
        return None
    try:
        approvals = json.loads(row['approvals_json'])
    except json.JSONDecodeError:
        return None
    return {
        'approvals': approvals,
        'cached_at': row['cached_at'],
    }


def save_related_approval_cache(
    db_path,
    cache_key,
    user_id,
    process_code,
    start_time,
    end_time,
    statuses,
    limit,
    approvals,
):
    cached_at = datetime.now().isoformat(timespec='seconds')
    with _connect(db_path) as connection:
        _ensure_schema(connection)
        connection.execute(
            '''
            INSERT INTO dingtalk_related_approval_cache (
                cache_key,
                user_id,
                process_code,
                start_time,
                end_time,
                statuses_json,
                limit_count,
                approvals_json,
                cached_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                user_id = excluded.user_id,
                process_code = excluded.process_code,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                statuses_json = excluded.statuses_json,
                limit_count = excluded.limit_count,
                approvals_json = excluded.approvals_json,
                cached_at = excluded.cached_at
            ''',
            (
                cache_key,
                user_id,
                process_code,
                start_time,
                end_time,
                json.dumps(statuses or [], ensure_ascii=False),
                int(limit),
                json.dumps(approvals or [], ensure_ascii=False),
                cached_at,
            ),
        )
        connection.commit()
    return cached_at
