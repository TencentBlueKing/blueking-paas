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
from django.apps import apps
from django.conf import settings


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
            # db migrations are forbidden except in unit tests
            # And paas_wl migrations can only apply to workloads db
            return settings.RUNNING_TESTS and db == self._workloads_db_name

        # other migrations can not apply to workloads db
        if db == self._workloads_db_name:
            return False
        # This DBRouter can't handle the input args, return None (which means not participating in the decision)
        return None

    def _model_form_wl(self, model) -> bool:
        return model.__module__.startswith("paas_wl")

    def _app_from_wl(self, app_config) -> bool:
        return app_config.module.__name__.startswith("paas_wl")
