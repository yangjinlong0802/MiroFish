"""
MySQL 数据库核心模块
提供连接管理、通用查询/更新方法、以及所有表的初始化
"""

import pymysql
from typing import List, Optional

from .config import Config
from .utils.logger import get_logger

logger = get_logger('mirofish.database')


def get_connection():
    """
    获取 MySQL 连接（per-operation 短连接模式）。
    调用方负责 close()。
    """
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )


def execute_query(sql: str, params: tuple = None) -> List[dict]:
    """
    执行 SELECT 查询，返回 List[dict]。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


def execute_update(sql: str, params: tuple = None) -> int:
    """
    执行 INSERT / UPDATE / DELETE，返回 affected rows。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, params)
        conn.commit()
        return affected
    finally:
        conn.close()


# ==================== 建表 SQL ====================

_CREATE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS `projects` (
    `project_id`          VARCHAR(32) NOT NULL,
    `user_id`             VARCHAR(64) NOT NULL DEFAULT 'anonymous',
    `name`                VARCHAR(255) NOT NULL DEFAULT 'Unnamed Project',
    `status`              VARCHAR(32) NOT NULL DEFAULT 'created',
    `simulation_requirement` TEXT,
    `ontology`            JSON,
    `analysis_summary`    TEXT,
    `files`               JSON,
    `total_text_length`   INT UNSIGNED NOT NULL DEFAULT 0,
    `graph_id`            VARCHAR(128),
    `graph_build_task_id` VARCHAR(64),
    `chunk_size`          INT UNSIGNED NOT NULL DEFAULT 500,
    `chunk_overlap`       INT UNSIGNED NOT NULL DEFAULT 50,
    `error`               TEXT,
    `created_at`          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`project_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

_CREATE_SIMULATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS `simulations` (
    `simulation_id`   VARCHAR(32) NOT NULL,
    `project_id`      VARCHAR(32) NOT NULL,
    `user_id`         VARCHAR(64) NOT NULL DEFAULT 'anonymous',
    `graph_id`        VARCHAR(128) NOT NULL,
    `enable_twitter`  TINYINT(1) NOT NULL DEFAULT 1,
    `enable_reddit`   TINYINT(1) NOT NULL DEFAULT 1,
    `status`          VARCHAR(32) NOT NULL DEFAULT 'created',
    `entities_count`  INT UNSIGNED NOT NULL DEFAULT 0,
    `profiles_count`  INT UNSIGNED NOT NULL DEFAULT 0,
    `entity_types`    JSON,
    `config_generated` TINYINT(1) NOT NULL DEFAULT 0,
    `config_reasoning` TEXT,
    `current_round`   INT UNSIGNED NOT NULL DEFAULT 0,
    `twitter_status`  VARCHAR(32) NOT NULL DEFAULT 'not_started',
    `reddit_status`   VARCHAR(32) NOT NULL DEFAULT 'not_started',
    `error`           TEXT,
    `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`simulation_id`),
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

_CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS `tasks` (
    `task_id`         VARCHAR(64) NOT NULL,
    `task_type`       VARCHAR(128) NOT NULL DEFAULT '',
    `status`          VARCHAR(32) NOT NULL DEFAULT 'pending',
    `progress`        TINYINT UNSIGNED NOT NULL DEFAULT 0,
    `message`         TEXT,
    `result`          JSON,
    `error`           TEXT,
    `metadata`        JSON,
    `progress_detail` JSON,
    `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`task_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

_CREATE_OPERATION_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS `operation_logs` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `client_ip` VARCHAR(64) NOT NULL COMMENT '客户端IP',
    `action_name` VARCHAR(64) NOT NULL COMMENT '操作名称',
    `task_params` JSON DEFAULT NULL COMMENT '核心业务参数',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    PRIMARY KEY (`id`),
    INDEX `idx_client_ip` (`client_ip`),
    INDEX `idx_action_name` (`action_name`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='核心业务操作日志表';
"""


def init_tables() -> bool:
    """
    初始化所有 MySQL 表（含 operation_logs）。
    应在 Flask 应用启动时调用。

    Returns:
        True 表示成功，False 表示跳过或失败
    """
    if not Config.MYSQL_PASSWORD or Config.MYSQL_PASSWORD == 'your_password_here':
        logger.warning("MySQL 密码未配置，跳过数据库初始化。请在 .env 中设置 MYSQL_PASSWORD")
        return False

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(_CREATE_PROJECTS_TABLE)
            cursor.execute(_CREATE_SIMULATIONS_TABLE)
            cursor.execute(_CREATE_TASKS_TABLE)
            cursor.execute(_CREATE_OPERATION_LOGS_TABLE)
        conn.commit()
        conn.close()
        logger.info("MySQL 全部表初始化成功（projects, simulations, tasks, operation_logs）")
        return True
    except Exception as e:
        logger.warning(f"MySQL 数据库初始化失败: {e}")
        return False
