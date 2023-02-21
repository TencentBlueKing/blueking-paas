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


class WorkloadsDBRouter:
    """
    A router to control all database operations on workloads models
    """

    _workloads_db_name = "workloads"

    def db_for_read(self, model, **hints):
        """Route the db for read"""
        if self._should_handle_model(model):
            return self._workloads_db_name
        return None

    def db_for_write(self, model, **hints):
        """Route the db for write"""
        if self._should_handle_model(model):
            return self._workloads_db_name
        return None

    def allow_relation(self, obj1, obj2, **hint):
        """allow relations if obj1 and obj2 are both workloads models"""
        if self._should_handle_model(obj1) and self._should_handle_model(obj2):
            return True
        return None

    def allow_migrate(self, db, app_label, model, **hints):
        """Migration is forbidden now"""
        if self._should_handle_model(model):
            return False
        return None

    def _should_handle_model(self, model):
        return model.__module__.startswith("paas_wl")
