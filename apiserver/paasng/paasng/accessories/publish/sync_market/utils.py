# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import logging
from collections import defaultdict
from functools import partial, wraps

from django.conf import settings
from sqlalchemy.orm import Session

from paasng.accessories.publish.sync_market.managers import AppManger
from paasng.core.core.storages.sqlalchemy import console_db

logger = logging.getLogger(__name__)


def run_required_db_console_config(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # BK_CONSOLE_DBCONF has a default value of None
        if not getattr(settings, "BK_CONSOLE_DBCONF", None):
            func_name = func.func.__name__ if isinstance(func, partial) else func.__name__
            logger.warning("BK_CONSOLE_DB_CONF not provided, skip running %s", func_name)
            return None
        else:
            return func(*args, **kwargs)

    return wrapper


@run_required_db_console_config
def set_migrated_state(code, is_migrated):
    """this is a tool function for legacy migration"""
    with console_db.session_scope() as session:
        count = AppManger(session).update(code, {"migrated_to_paasv3": is_migrated})
        logger.info("成功更新应用%s的迁移状态为: %s, 影响记录%s条", code, is_migrated, count)


class LegacyDBCascadeDeleter:
    def __init__(self, session: Session, table_name: str):
        self.session = session
        self.table_name = table_name

    def cascade_delete_by_id(self, record_id: int, dry_run: bool) -> dict:
        """根据 id 从 db 中级联删除记录"""
        deleted_records: dict = defaultdict(list)
        try:
            # 构建完整的依赖关系图
            dependency_graph = self._build_dependency_graph(self.table_name)

            # 递归删除
            self._delete_records_recursively(dependency_graph, self.table_name, record_id, deleted_records, dry_run)
            self.session.commit()

        except Exception:
            self.session.rollback()
            raise
        if not dry_run:
            logger.info("成功删除 legacy db 记录: %s", deleted_records)
        return deleted_records

    def _get_foreign_key_references(self, target_table: str):
        """获取所有引用目标表的外键关系"""
        sql = """
        SELECT
            TABLE_NAME,
            COLUMN_NAME,
            REFERENCED_TABLE_NAME,
            REFERENCED_COLUMN_NAME
        FROM
            INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE
            REFERENCED_TABLE_NAME = :target_table
        AND TABLE_SCHEMA = DATABASE()
        """
        result = self.session.execute(sql, {"target_table": target_table})
        return [dict(row) for row in result]

    def _build_dependency_graph(self, start_table: str) -> dict:
        """构建完整的依赖关系图"""
        graph = defaultdict(list)
        visited = set()

        def dfs(current_table):
            if current_table in visited:
                return
            visited.add(current_table)
            references = self._get_foreign_key_references(current_table)
            for ref in references:
                graph[current_table].append(
                    {
                        "referencing_table": ref["TABLE_NAME"],
                        "foreign_key_column": ref["COLUMN_NAME"],
                        "referenced_column": ref["REFERENCED_COLUMN_NAME"],
                    }
                )
                dfs(ref["TABLE_NAME"])

        dfs(start_table)
        return graph

    def _find_records_referencing(self, table: str, column: str, referenced_id: int):
        """查找引用特定 ID 的记录"""
        sql = f"SELECT id FROM {table} WHERE {column} = :ref_id"
        result = self.session.execute(sql, {"ref_id": referenced_id})
        return [row[0] for row in result]

    def _delete_records(self, table: str, column: str, referenced_id: int):
        """删除引用特定 ID 的记录"""
        sql = f"DELETE FROM {table} WHERE {column} = :ref_id"
        self.session.execute(sql, {"ref_id": referenced_id})

    def _delete_records_recursively(
        self, graph: dict, table: str, record_id: int, deleted_records: dict, dry_run: bool
    ):
        """递归删除记录"""
        deleted_records[table].append(record_id)
        # 该表没有被其他表引用，直接删除记录
        if table not in graph:
            self._delete_records(table, "id", record_id)
            return

        # 先处理所有引用该表的记录
        for ref in graph[table]:
            referencing_table = ref["referencing_table"]
            foreign_key_column = ref["foreign_key_column"]

            # 查找所有引用当前记录的记录
            referenced_ids = self._find_records_referencing(referencing_table, foreign_key_column, record_id)

            for ref_id in referenced_ids:
                self._delete_records_recursively(graph, referencing_table, ref_id, deleted_records, dry_run)

        # 所有引用记录都删除后，删除当前记录
        self._delete_records(table, "id", record_id)


def cascade_delete_legacy_app(field: str, value: str, dry_run: bool = True) -> dict:
    """删除指定字段值对应的应用记录，如果多条记录只会删除第一个"""
    with console_db.session_scope() as session:
        mgr = AppManger(session)
        app = mgr.session.query(mgr.model).filter_by(**{field: value}).scalar()
        if not app:
            return {}
        return LegacyDBCascadeDeleter(session, mgr.model.__name__).cascade_delete_by_id(app.id, dry_run)
