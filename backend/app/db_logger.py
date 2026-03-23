"""
MySQL 操作日志模块
仅针对高价值、消耗大模型资源的核心业务接口记录日志，避免海量无效日志
"""

import json
import threading
from datetime import datetime
from typing import Optional

from flask import request

from .config import Config
from .utils.logger import get_logger

logger = get_logger('mirofish.db_logger')


def _get_client_ip() -> str:
    """
    获取客户端真实 IP，优先从反向代理头中提取。
    """
    # 优先从反向代理头中获取真实 IP
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    real_ip = request.headers.get('X-Real-IP', '')
    if real_ip:
        return real_ip.strip()

    return request.remote_addr or 'unknown'


def log_action(action_name: str, task_params: Optional[dict] = None):
    """
    记录核心业务操作到 MySQL（异步，不阻塞主线程）。

    自动从当前 Flask 请求上下文中提取 client_ip。

    Args:
        action_name: 操作名称（如 start_simulation, generate_report）
        task_params: 核心业务参数（将序列化为 JSON）
    """
    # 在主线程中提取 request 上下文信息（子线程无法访问 Flask request）
    client_ip = _get_client_ip()

    def _insert():
        try:
            if not Config.MYSQL_PASSWORD or Config.MYSQL_PASSWORD == 'your_password_here':
                return

            from .database import get_connection

            params_json = json.dumps(task_params, ensure_ascii=False) if task_params else None
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO `operation_logs` (`client_ip`, `action_name`, `task_params`, `created_at`) "
                    "VALUES (%s, %s, %s, %s)",
                    (client_ip, action_name, params_json, datetime.now())
                )
            conn.commit()
            conn.close()
            logger.debug(f"操作日志已记录: ip={client_ip}, action={action_name}")
        except Exception as e:
            logger.warning(f"记录操作日志失败: {e}")

    # 在后台线程中执行，避免阻塞请求
    thread = threading.Thread(target=_insert, daemon=True)
    thread.start()
