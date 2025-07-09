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

import datetime
import logging
from collections import defaultdict
from dataclasses import asdict
from typing import Optional

from django.utils.translation import get_language

from paasng.accessories.publish.market.models import Tag
from paasng.accessories.publish.sync_market.models import TagData, TagMap

try:
    from paasng.infras.legacydb_te.adaptors import (
        AppAdaptor,
        AppDeveloperAdaptor,
        AppEnvVarAdaptor,
        AppOpsAdaptor,
        AppReleaseRecordAdaptor,
        AppSecureInfoAdaptor,
        AppTagAdaptor,
        AppUseRecordAdaptor,
        EngineAppAdaptor,
    )
except ImportError:
    from paasng.infras.legacydb.adaptors import (  # type: ignore
        AppAdaptor,
        AppDeveloperAdaptor,
        AppEnvVarAdaptor,
        AppOpsAdaptor,
        AppReleaseRecordAdaptor,
        AppSecureInfoAdaptor,
        AppTagAdaptor,
        AppUseRecordAdaptor,
        EngineAppAdaptor,
    )

logger = logging.getLogger(__name__)


class AppTagManger(AppTagAdaptor):
    def create_tagmap(self, tag_data: TagData):
        tag_dict = asdict(tag_data)
        # 是否为二级分类
        if tag_data.parent_id:
            parent = TagMap.objects.get(remote_id=tag_data.parent_id).tag
            tag_dict["parent"] = parent
        else:
            tag_dict["parent"] = None
        tag_dict.pop("parent_id", "")
        tag_dict.pop("id", None)
        tag = Tag.objects.create(**tag_dict)

        TagMap.objects.create(tag=tag, remote_id=tag_data.id)
        return True

    def sync_tags_from_console(self):
        """同步应用分类"""
        # 获取应用分类列表，不同版本需要差异化实现
        tag_list = self.get_tag_list()
        for tag in tag_list:
            try:
                rel = TagMap.objects.get(remote_id=tag.id)
                if rel.tag.name != tag.name:
                    old_name = rel.tag.name
                    # 更新分类名称
                    rel.tag.name = tag.name
                    rel.tag.save()
                    logger.info(f"Tag name is updated from {old_name} to {tag.name}")
            except TagMap.DoesNotExist:
                self.create_tagmap(tag)
                logger.info(f"add new tag, name is {tag.name}")

    def get_tag_by_name(self, name: str):
        """根据名称获取 tag 信息"""
        tag = self.session.query(self.model).filter_by(name=name).scalar()
        return tag

    def create_tag(self, tag_data: dict):
        """创建 tag，主要用于单元测试初始化数据"""
        tag = self.model(**tag_data)
        self.session.add(tag)
        return tag


class AppDeveloperManger(AppDeveloperAdaptor):
    """应用开发者"""


class AppOpsManger(AppOpsAdaptor):
    """应用运营者"""


class AppManger(AppAdaptor):
    """应用"""

    def get(self, code: str):
        app = self.session.query(self.model).filter_by(code=code).scalar()
        return app

    def verify_name_is_unique(self, name: str, code: Optional[str] = None) -> bool:
        qs = self.session.query(self.model)
        if code:
            qs = qs.filter(self.model.code != code)
        app = qs.filter_by(name=name).scalar()
        return not app

    def delete_by_code(self, code: str):
        """根据 code 从 DB 中删除应用"""
        self.session.query(self.model).filter_by(code=code).delete()
        self.session.commit()

    def delete_by_name(self, name: str):
        """根据 name 从 DB 中删除应用"""
        self.session.query(self.model).filter_by(name=name).delete()
        self.session.commit()

    def cascade_delete_by_code(self, code: str):
        """根据 id 从 db 中级联删除应用"""
        app = self.session.query(self.model).filter_by(code=code).scalar()
        self.cascade_delete_by_id(app.id)

    def cascade_delete_by_id(self, app_id: int):
        """根据 id 从 db 中级联删除应用"""
        try:
            # 构建完整的依赖关系图
            dependency_graph = self._build_dependency_graph("app_app")

            # 递归删除
            self._delete_records_recursively(dependency_graph, self.model.__name__, app_id)
            self.session.commit()

        except Exception:
            self.session.rollback()
            raise

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

    def _build_dependency_graph(self, start_table: str):
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
        """查找引用特定ID的记录"""
        sql = f"SELECT id FROM {table} WHERE {column} = :ref_id"
        result = self.session.execute(sql, {"ref_id": referenced_id})
        return [row[0] for row in result]

    def _delete_records_recursively(self, graph: dict, table: str, record_id: int):
        """递归删除记录"""
        # 存在循环依赖的情况，因此当没有记录时打断递归
        referenced_ids = self._find_records_referencing(table, "id", record_id)
        if not referenced_ids:
            return

        # 该表没有被其他表引用，直接删除记录
        if table not in graph:
            sql = f"DELETE FROM {table} WHERE id = :record_id"
            self.session.execute(sql, {"record_id": record_id})
            return

        # 先处理所有引用这个表的记录
        for ref in graph[table]:
            referencing_table = ref["referencing_table"]
            foreign_key_column = ref["foreign_key_column"]

            # 查找所有引用当前记录的记录
            referenced_ids = self._find_records_referencing(referencing_table, foreign_key_column, record_id)

            for ref_id in referenced_ids:
                self._delete_records_recursively(graph, referencing_table, ref_id)

        # 所有引用记录都删除后，删除当前记录
        sql = f"DELETE FROM {table} WHERE id = :record_id"
        self.session.execute(sql, {"record_id": record_id})


class AppUseRecordManger(AppUseRecordAdaptor):
    """应用访问记录"""

    def get_app_records(self, application_codes: list, days_before: int, limit: int):
        dt_before = datetime.date.today() - datetime.timedelta(days=days_before)
        result = self.get_records(application_codes, dt_before, limit)
        if get_language() == "en":
            data = [{"application_code": item[0], "application_name": item[2], "pv": item[3]} for item in result]
        else:
            data = [{"application_code": item[0], "application_name": item[1], "pv": item[3]} for item in result]
        return data


class AppReleaseRecordManger(AppReleaseRecordAdaptor):
    """应用部署记录
    应用正式环境部署成功后将操作记录同步到 console , 这样桌面才能显示：首次上线/提测时间、最近上线时间，并展示最新应用tab
    """


class AppEnvVarManger(AppEnvVarAdaptor):
    """应用自定义环境变量"""


class AppSecureInfoManger(AppSecureInfoAdaptor):
    """应用安全信息,如 DB 信息等"""


class EngineAppManger(EngineAppAdaptor):
    """App engine 中保存的应用信息"""
