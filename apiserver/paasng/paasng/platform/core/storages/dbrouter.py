# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from types import MethodType
from typing import Tuple

from django.apps import apps
from django.db import connections
from django.db.migrations.loader import MigrationRecorder
from django.db.migrations.operations.base import Operation


def operation_router(model_operation: Operation, migration_record_sentinel: Tuple[str, str]):
    """A router to control whether to apply database_forwards on workloads db.

    由于架构调整, workloads.services(k8s ingress 模块) 重命名为 ingress, 以避免与 apiserver 中的 services(增强服务模块) 重名冲突
    应用重命名会导致 migrations 重复执行, 因此需要 patch `Opration.allow_migrate_model` 方法, 在哨兵记录存在时跳过操作

    哨兵值为 `django_migrations` 表的记录, 用于判断重命名前的 migrations 是否已执行
    如在 0005_auto_20221212_1810.py 中应该使用 ("services", "0005_auto_20221212_1810") 作为哨兵值

    Note:
    1. 无论是否跳过 operation 的执行, 在执行 db migrate 后均会产生 ingress app 的 migrations 记录
    2. 新增的 migrations 无需进行 patch
    """
    origin_allow_migrate_model = model_operation.allow_migrate_model

    def allow_migrate_model(self, connection_alias, model):
        if connection_alias != WorkloadsDBRouter()._workloads_db_name:
            return False

        connection = connections[connection_alias]
        # 如果哨兵记录已存在, 表示该环境并未全新部署. 跳过执行 operation
        if (
            MigrationRecorder(connection)
            .migration_qs.filter(app=migration_record_sentinel[0], name=migration_record_sentinel[1])
            .exists()
        ):
            return False
        return origin_allow_migrate_model(connection_alias, model)

    model_operation.allow_migrate_model = MethodType(allow_migrate_model, model_operation)
    return model_operation


class WorkloadsDBRouter:
    """
    A router to control all database operations on workloads models
    """

    _workloads_db_name = "workloads"

    def db_for_read(self, model, **hints):
        """Route the db for read"""
        if self._model_form_wl(model):
            return self._workloads_db_name
        return None

    def db_for_write(self, model, **hints):
        """Route the db for write"""
        if self._model_form_wl(model):
            return self._workloads_db_name
        return None

    def allow_relation(self, obj1, obj2, **hint):
        """allow relations if obj1 and obj2 are both workloads models"""
        if self._model_form_wl(obj1) and self._model_form_wl(obj2):
            return True
        return None

    def allow_migrate(self, db, app_label, **hints):
        app_config = apps.get_app_config(app_label)
        if self._app_from_wl(app_config):
            # workloads db migrations are forbidden except apply to workloads db
            return db == self._workloads_db_name

        # other migrations can not apply to workloads db
        if db == self._workloads_db_name:
            return False
        # This DBRouter can't handle the input args, return None (which means not participating in the decision)
        return None

    def _model_form_wl(self, model) -> bool:
        return model.__module__.startswith("paas_wl")

    def _app_from_wl(self, app_config) -> bool:
        return app_config.module.__name__.startswith("paas_wl")
