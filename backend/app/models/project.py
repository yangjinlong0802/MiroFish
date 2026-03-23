"""
项目上下文管理
元数据存储在 MySQL projects 表中，大文件留在磁盘
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from ..config import Config
from ..database import execute_query, execute_update


class ProjectStatus(str, Enum):
    """项目状态"""
    CREATED = "created"              # 刚创建，文件已上传
    ONTOLOGY_GENERATED = "ontology_generated"  # 本体已生成
    GRAPH_BUILDING = "graph_building"    # 图谱构建中
    GRAPH_COMPLETED = "graph_completed"  # 图谱构建完成
    FAILED = "failed"                # 失败


@dataclass
class Project:
    """项目数据模型"""
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    user_id: str = 'anonymous'

    # 文件信息
    files: List[Dict[str, str]] = field(default_factory=list)  # [{filename, path, size}]
    total_text_length: int = 0

    # 本体信息（接口1生成后填充）
    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None

    # 图谱信息（接口2完成后填充）
    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None

    # 配置
    simulation_requirement: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50

    # 错误信息
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "files": self.files,
            "total_text_length": self.total_text_length,
            "ontology": self.ontology,
            "analysis_summary": self.analysis_summary,
            "graph_id": self.graph_id,
            "graph_build_task_id": self.graph_build_task_id,
            "simulation_requirement": self.simulation_requirement,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "error": self.error
        }


def _parse_json(val):
    """安全解析 JSON 字段"""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _row_to_project(row: dict) -> Project:
    """将数据库行转换为 Project 对象"""
    status = row.get('status', 'created')
    if isinstance(status, str):
        status = ProjectStatus(status)

    created_at = row.get('created_at')
    updated_at = row.get('updated_at')
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    return Project(
        project_id=row['project_id'],
        name=row.get('name', 'Unnamed Project'),
        status=status,
        created_at=created_at or '',
        updated_at=updated_at or '',
        user_id=row.get('user_id', 'anonymous'),
        files=_parse_json(row.get('files')) or [],
        total_text_length=row.get('total_text_length', 0),
        ontology=_parse_json(row.get('ontology')),
        analysis_summary=row.get('analysis_summary'),
        graph_id=row.get('graph_id'),
        graph_build_task_id=row.get('graph_build_task_id'),
        simulation_requirement=row.get('simulation_requirement'),
        chunk_size=row.get('chunk_size', 500),
        chunk_overlap=row.get('chunk_overlap', 50),
        error=row.get('error'),
    )


class ProjectManager:
    """项目管理器 - 元数据存 MySQL，文件存磁盘"""

    # 项目存储根目录
    PROJECTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'projects')

    @classmethod
    def _ensure_projects_dir(cls):
        """确保项目目录存在"""
        os.makedirs(cls.PROJECTS_DIR, exist_ok=True)

    @classmethod
    def _get_project_dir(cls, project_id: str) -> str:
        """获取项目目录路径"""
        return os.path.join(cls.PROJECTS_DIR, project_id)

    @classmethod
    def _get_project_files_dir(cls, project_id: str) -> str:
        """获取项目文件存储目录"""
        return os.path.join(cls._get_project_dir(project_id), 'files')

    @classmethod
    def _get_project_text_path(cls, project_id: str) -> str:
        """获取项目提取文本存储路径"""
        return os.path.join(cls._get_project_dir(project_id), 'extracted_text.txt')

    @classmethod
    def create_project(cls, name: str = "Unnamed Project", user_id: str = 'anonymous') -> Project:
        """
        创建新项目

        Args:
            name: 项目名称
            user_id: 用户ID

        Returns:
            新创建的Project对象
        """
        cls._ensure_projects_dir()

        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now,
            user_id=user_id,
        )

        # 创建项目目录结构
        project_dir = cls._get_project_dir(project_id)
        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(files_dir, exist_ok=True)

        # INSERT 到 MySQL
        execute_update(
            "INSERT INTO `projects` "
            "(`project_id`, `user_id`, `name`, `status`, `files`, `created_at`, `updated_at`) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (project_id, user_id, name, ProjectStatus.CREATED.value,
             json.dumps([], ensure_ascii=False), now, now)
        )

        return project

    @classmethod
    def save_project(cls, project: Project) -> None:
        """保存（更新）项目元数据到 MySQL"""
        project.updated_at = datetime.now().isoformat()

        status_val = project.status.value if isinstance(project.status, ProjectStatus) else project.status
        ontology_json = json.dumps(project.ontology, ensure_ascii=False) if project.ontology else None
        files_json = json.dumps(project.files, ensure_ascii=False) if project.files else '[]'

        execute_update(
            "UPDATE `projects` SET "
            "`name` = %s, `status` = %s, `simulation_requirement` = %s, "
            "`ontology` = %s, `analysis_summary` = %s, `files` = %s, "
            "`total_text_length` = %s, `graph_id` = %s, `graph_build_task_id` = %s, "
            "`chunk_size` = %s, `chunk_overlap` = %s, `error` = %s, `updated_at` = %s "
            "WHERE `project_id` = %s",
            (
                project.name, status_val, project.simulation_requirement,
                ontology_json, project.analysis_summary, files_json,
                project.total_text_length, project.graph_id, project.graph_build_task_id,
                project.chunk_size, project.chunk_overlap, project.error,
                project.updated_at, project.project_id
            )
        )

    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        """
        获取项目

        Args:
            project_id: 项目ID

        Returns:
            Project对象，如果不存在返回None
        """
        rows = execute_query(
            "SELECT * FROM `projects` WHERE `project_id` = %s",
            (project_id,)
        )
        if not rows:
            return None
        return _row_to_project(rows[0])

    @classmethod
    def list_projects(cls, limit: int = 50, user_id: Optional[str] = None) -> List[Project]:
        """
        列出项目

        Args:
            limit: 返回数量限制
            user_id: 按用户过滤（None 表示不过滤）

        Returns:
            项目列表，按创建时间倒序
        """
        if user_id:
            rows = execute_query(
                "SELECT * FROM `projects` WHERE `user_id` = %s ORDER BY `created_at` DESC LIMIT %s",
                (user_id, limit)
            )
        else:
            rows = execute_query(
                "SELECT * FROM `projects` ORDER BY `created_at` DESC LIMIT %s",
                (limit,)
            )
        return [_row_to_project(r) for r in rows]

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        """
        删除项目及其所有文件

        Args:
            project_id: 项目ID

        Returns:
            是否删除成功
        """
        # 先从 MySQL 删除
        affected = execute_update(
            "DELETE FROM `projects` WHERE `project_id` = %s",
            (project_id,)
        )

        # 删除磁盘目录
        project_dir = cls._get_project_dir(project_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)

        return affected > 0

    @classmethod
    def save_file_to_project(cls, project_id: str, file_storage, original_filename: str) -> Dict[str, str]:
        """
        保存上传的文件到项目目录

        Args:
            project_id: 项目ID
            file_storage: Flask的FileStorage对象
            original_filename: 原始文件名

        Returns:
            文件信息字典 {filename, path, size}
        """
        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(files_dir, exist_ok=True)

        # 生成安全的文件名
        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(files_dir, safe_filename)

        # 保存文件
        file_storage.save(file_path)

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": file_path,
            "size": file_size
        }

    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        """保存提取的文本"""
        text_path = cls._get_project_text_path(project_id)
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)

    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        """获取提取的文本"""
        text_path = cls._get_project_text_path(project_id)

        if not os.path.exists(text_path):
            return None

        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        """获取项目的所有文件路径"""
        files_dir = cls._get_project_files_dir(project_id)

        if not os.path.exists(files_dir):
            return []

        return [
            os.path.join(files_dir, f)
            for f in os.listdir(files_dir)
            if os.path.isfile(os.path.join(files_dir, f))
        ]
