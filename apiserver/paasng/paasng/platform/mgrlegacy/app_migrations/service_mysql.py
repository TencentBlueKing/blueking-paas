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

from django.utils.translation import gettext_lazy as _

from paasng.accessories.publish.sync_market.managers import AppSecureInfoManger
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.engine.models.config_var import ConfigVar
from paasng.platform.mgrlegacy.app_migrations.service import BaseRemoteServiceMigration

logger = logging.getLogger(__name__)


class MysqlServiceMigration(BaseRemoteServiceMigration):
    """only enabled for smart app(not normal app)"""

    service_name = "mysql"

    def get_description(self):
        return "同步 MySQL 配置"

    def should_skip(self):
        return not self.legacy_app.is_saas

    def _add_envs(self, db_credentials: dict, environment_name: str):
        """添加环境变量"""
        # v2 中的环境变量 key 转换表
        key_maps = {
            "host": "DB_HOST",
            "port": "DB_PORT",
            "name": "DB_NAME",
            "user": "DB_USERNAME",
            "password": "DB_PASSWORD",
            "type": "DB_TYPE",
        }
        environment = self.context.app.envs.get(environment=environment_name)
        module = self.context.app.get_default_module()

        data = []
        for key in db_credentials:
            kwargs = {
                "key": key_maps.get(key, key),
                "value": db_credentials[key],
                "description": "Generated when migrating from PaaS2.0",
                "is_builtin": True,
                "module": module,
                "environment": environment,
                "is_global": False,
            }
            data.append(ConfigVar(**kwargs))
        ConfigVar.objects.bulk_create(data)

    def get_stag_service_instance_info(self):
        """"""

        obj = AppSecureInfoManger(self.context.session).get(self.context.legacy_app.code)
        db_pwd = self.context.legacy_app_proxy.get_unified_password()

        # NOTE: PaaS2.0 应用的测试库是特殊的, 其db_name并没有被存下来, 拼接规则为： {db_name}_bkt
        credentials = {
            "host": obj.db_host,
            "port": obj.db_port,
            "name": f"{obj.db_name}_bkt",
            "user": obj.db_username,
            "password": db_pwd,
        }

        if not self.context.legacy_app_proxy.has_stag_deployed():
            self.add_log(_("当前应用尚未部署过预发布环境, 跳过创建预发布环境的数据库实例。"))
            return None, None

        # 需要将DB信息写入到环境变量中, 需要注明 DB 类型
        db_credentials = {**credentials, "DB_TYPE": obj.db_type}
        self._add_envs(db_credentials, ConfigVarEnvName.STAG.value)
        return credentials, None

    def get_prod_service_instance_info(self):
        obj = AppSecureInfoManger(self.context.session).get(self.context.legacy_app.code)
        db_pwd = self.context.legacy_app_proxy.get_unified_password()

        credentials = {
            "host": obj.db_host,
            "port": obj.db_port,
            "name": obj.db_name,
            "user": obj.db_username,
            "password": db_pwd,
        }

        if not self.context.legacy_app_proxy.has_prod_deployed():
            self.add_log(_("当前应用尚未部署过生产环境, 跳过创建生产环境的数据库实例。"))
            return None, None

        # 需要将DB信息写入到环境变量中, 需要注明 DB 类型
        db_credentials = {**credentials, "DB_TYPE": obj.db_type}
        self._add_envs(db_credentials, ConfigVarEnvName.PROD.value)
        return credentials, None
