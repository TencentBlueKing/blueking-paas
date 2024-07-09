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

from django.conf import settings

from paasng.platform.mgrlegacy.app_migrations.envs_base import BaseEnvironmentVariableMigration


class DefaultEnvironmentVariableMigration(BaseEnvironmentVariableMigration):
    """私有化版本环境变量迁移，Mysql 和 RabbitMQ 的环境变量通过增强服务迁移"""

    def get_global_envs(self) -> dict:
        variables = dict(
            APP_ID=self.legacy_app.code,
            APP_TOKEN=self.context.legacy_app_proxy.get_secret_key(),
            BK_PAAS_HOST=settings.BK_PAAS2_URL,
            BK_PAAS_INNER_HOST=settings.BK_PAAS2_INNER_URL,
        )
        # PaaS2.0 注入的系统环境变量
        variables.update(settings.BK_PAAS2_PLATFORM_ENVS)
        return variables

    def get_stag_envs(self) -> dict:
        variables = dict(
            BK_ENV="testing",
        )
        return variables

    def get_prod_envs(self) -> dict:
        variables = dict(BK_ENV="production")
        return variables
