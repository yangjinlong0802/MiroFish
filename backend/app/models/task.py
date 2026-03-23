"""
任务状态管理
用于跟踪长时间运行的任务（如图谱构建）
元数据存储在 MySQL tasks 表中
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from ..database import execute_query, execute_update
from ..utils.logger import get_logger

logger = get_logger('mirofish.task')


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待中
    PROCESSING = "processing"    # 处理中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败


@dataclass
class Task:
    """任务数据类"""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0              # 总进度百分比 0-100
    message: str = ""              # 状态消息
    result: Optional[Dict] = None  # 任务结果
    error: Optional[str] = None    # 错误信息
    metadata: Dict = field(default_factory=dict)  # 额外元数据
    progress_detail: Dict = field(default_factory=dict)  # 详细进度信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


def _row_to_task(row: dict) -> Task:
    """将数据库行转换为 Task 对象"""
    def _parse_json(val, default=None):
        if val is None:
            return default
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return default
        return default

    return Task(
        task_id=row['task_id'],
        task_type=row.get('task_type', ''),
        status=TaskStatus(row.get('status', 'pending')),
        created_at=row['created_at'],
        updated_at=row['updated_at'],
        progress=row.get('progress', 0),
        message=row.get('message', '') or '',
        result=_parse_json(row.get('result'), default=None),
        error=row.get('error'),
        metadata=_parse_json(row.get('metadata'), default={}) or {},
        progress_detail=_parse_json(row.get('progress_detail'), default={}) or {},
    )


class TaskManager:
    """
    任务管理器
    所有状态持久化到 MySQL tasks 表
    """

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        """
        创建新任务

        Args:
            task_type: 任务类型
            metadata: 额外元数据

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        execute_update(
            "INSERT INTO `tasks` (`task_id`, `task_type`, `status`, `progress`, `metadata`) "
            "VALUES (%s, %s, %s, %s, %s)",
            (task_id, task_type, TaskStatus.PENDING.value, 0, meta_json)
        )

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        rows = execute_query(
            "SELECT * FROM `tasks` WHERE `task_id` = %s",
            (task_id,)
        )
        if not rows:
            return None
        return _row_to_task(rows[0])

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict] = None
    ):
        """
        更新任务状态
        """
        sets: List[str] = []
        params: list = []

        if status is not None:
            sets.append("`status` = %s")
            params.append(status.value)
        if progress is not None:
            sets.append("`progress` = %s")
            params.append(progress)
        if message is not None:
            sets.append("`message` = %s")
            params.append(message)
        if result is not None:
            sets.append("`result` = %s")
            params.append(json.dumps(result, ensure_ascii=False))
        if error is not None:
            sets.append("`error` = %s")
            params.append(error)
        if progress_detail is not None:
            sets.append("`progress_detail` = %s")
            params.append(json.dumps(progress_detail, ensure_ascii=False))

        if not sets:
            return

        params.append(task_id)
        sql = f"UPDATE `tasks` SET {', '.join(sets)} WHERE `task_id` = %s"
        execute_update(sql, tuple(params))

    def complete_task(self, task_id: str, result: Dict):
        """标记任务完成"""
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="任务完成",
            result=result
        )

    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="任务失败",
            error=error
        )

    def list_tasks(self, task_type: Optional[str] = None) -> list:
        """列出任务"""
        if task_type:
            rows = execute_query(
                "SELECT * FROM `tasks` WHERE `task_type` = %s ORDER BY `created_at` DESC",
                (task_type,)
            )
        else:
            rows = execute_query(
                "SELECT * FROM `tasks` ORDER BY `created_at` DESC"
            )
        return [_row_to_task(r) for r in rows]

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        execute_update(
            "DELETE FROM `tasks` WHERE `created_at` < %s AND `status` IN (%s, %s)",
            (cutoff, TaskStatus.COMPLETED.value, TaskStatus.FAILED.value)
        )
