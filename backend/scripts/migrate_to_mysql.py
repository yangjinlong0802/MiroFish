#!/usr/bin/env python3
"""
迁移脚本：将旧的 JSON 文件元数据导入 MySQL

用法：
    cd backend
    python -m scripts.migrate_to_mysql

迁移内容：
- uploads/projects/*/project.json → projects 表
- uploads/simulations/*/state.json → simulations 表
- Tasks 无需迁移（原本就是内存态）
"""

import os
import sys
import json

# 将 backend/ 加入 sys.path 以便导入 app 模块
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.config import Config
from app.database import get_connection, init_tables


def migrate_projects():
    """扫描 uploads/projects/*/project.json → INSERT 到 projects 表"""
    projects_dir = os.path.join(Config.UPLOAD_FOLDER, 'projects')
    if not os.path.exists(projects_dir):
        print(f"[跳过] 项目目录不存在: {projects_dir}")
        return 0

    conn = get_connection()
    migrated = 0
    skipped = 0

    for project_id in os.listdir(projects_dir):
        meta_path = os.path.join(projects_dir, project_id, 'project.json')
        if not os.path.isfile(meta_path):
            continue

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            pid = data.get('project_id', project_id)

            # 检查是否已存在
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM `projects` WHERE `project_id` = %s", (pid,))
                if cur.fetchone():
                    skipped += 1
                    continue

            ontology = data.get('ontology')
            ontology_json = json.dumps(ontology, ensure_ascii=False) if ontology else None
            files = data.get('files', [])
            files_json = json.dumps(files, ensure_ascii=False)

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO `projects` "
                    "(`project_id`, `user_id`, `name`, `status`, `simulation_requirement`, "
                    "`ontology`, `analysis_summary`, `files`, `total_text_length`, "
                    "`graph_id`, `graph_build_task_id`, `chunk_size`, `chunk_overlap`, "
                    "`error`, `created_at`, `updated_at`) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        pid,
                        'anonymous',
                        data.get('name', 'Unnamed Project'),
                        data.get('status', 'created'),
                        data.get('simulation_requirement'),
                        ontology_json,
                        data.get('analysis_summary'),
                        files_json,
                        data.get('total_text_length', 0),
                        data.get('graph_id'),
                        data.get('graph_build_task_id'),
                        data.get('chunk_size', 500),
                        data.get('chunk_overlap', 50),
                        data.get('error'),
                        data.get('created_at', '2025-01-01 00:00:00'),
                        data.get('updated_at', '2025-01-01 00:00:00'),
                    )
                )
            conn.commit()
            migrated += 1
            print(f"  [OK] project: {pid} - {data.get('name', '')}")

        except Exception as e:
            print(f"  [ERR] project {project_id}: {e}")

    conn.close()
    print(f"Projects 迁移完成: {migrated} 成功, {skipped} 已存在跳过")
    return migrated


def migrate_simulations():
    """扫描 uploads/simulations/*/state.json → INSERT 到 simulations 表"""
    sims_dir = os.path.join(Config.UPLOAD_FOLDER, 'simulations')
    if not os.path.exists(sims_dir):
        print(f"[跳过] 模拟目录不存在: {sims_dir}")
        return 0

    conn = get_connection()
    migrated = 0
    skipped = 0

    for sim_id in os.listdir(sims_dir):
        sim_path = os.path.join(sims_dir, sim_id)
        if not os.path.isdir(sim_path):
            continue

        state_path = os.path.join(sim_path, 'state.json')
        if not os.path.isfile(state_path):
            continue

        try:
            with open(state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            sid = data.get('simulation_id', sim_id)

            # 检查是否已存在
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM `simulations` WHERE `simulation_id` = %s", (sid,))
                if cur.fetchone():
                    skipped += 1
                    continue

            entity_types = data.get('entity_types', [])
            entity_types_json = json.dumps(entity_types, ensure_ascii=False)

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO `simulations` "
                    "(`simulation_id`, `project_id`, `user_id`, `graph_id`, "
                    "`enable_twitter`, `enable_reddit`, `status`, "
                    "`entities_count`, `profiles_count`, `entity_types`, "
                    "`config_generated`, `config_reasoning`, "
                    "`current_round`, `twitter_status`, `reddit_status`, "
                    "`error`, `created_at`, `updated_at`) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        sid,
                        data.get('project_id', ''),
                        'anonymous',
                        data.get('graph_id', ''),
                        int(data.get('enable_twitter', True)),
                        int(data.get('enable_reddit', True)),
                        data.get('status', 'created'),
                        data.get('entities_count', 0),
                        data.get('profiles_count', 0),
                        entity_types_json,
                        int(data.get('config_generated', False)),
                        data.get('config_reasoning', ''),
                        data.get('current_round', 0),
                        data.get('twitter_status', 'not_started'),
                        data.get('reddit_status', 'not_started'),
                        data.get('error'),
                        data.get('created_at', '2025-01-01 00:00:00'),
                        data.get('updated_at', '2025-01-01 00:00:00'),
                    )
                )
            conn.commit()
            migrated += 1
            print(f"  [OK] simulation: {sid} (project={data.get('project_id', '')})")

        except Exception as e:
            print(f"  [ERR] simulation {sim_id}: {e}")

    conn.close()
    print(f"Simulations 迁移完成: {migrated} 成功, {skipped} 已存在跳过")
    return migrated


def main():
    print("=" * 60)
    print("MiroFish JSON → MySQL 迁移工具")
    print("=" * 60)

    # 初始化表结构
    print("\n[1/3] 初始化 MySQL 表结构...")
    if not init_tables():
        print("错误: MySQL 初始化失败，请检查 .env 中的数据库配置")
        sys.exit(1)
    print("表结构初始化成功")

    # 迁移 Projects
    print("\n[2/3] 迁移 Projects...")
    migrate_projects()

    # 迁移 Simulations
    print("\n[3/3] 迁移 Simulations...")
    migrate_simulations()

    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
