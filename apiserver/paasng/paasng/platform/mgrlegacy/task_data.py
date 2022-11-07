# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from .app_migrations.basic import BaseObjectMigration, MainInfoMigration
from .app_migrations.egress_gateway import EgressGatewayMigration
from .app_migrations.envs import DefaultEnvironmentVariableMigration
from .app_migrations.market import MarketMigration
from .app_migrations.product import ProductMigration
from .app_migrations.service_mysql import MysqlServiceMigration
from .app_migrations.service_rabbitmq import RabbitMQServiceMigration
from .app_migrations.sourcectl import SourceControlMigration

# 应用迁移步骤
MIGRATION_CLASSES_LIST = [
    BaseObjectMigration,
    MainInfoMigration,
    SourceControlMigration,
    ProductMigration,
    DefaultEnvironmentVariableMigration,
    # TODO 增强服务迁移
    MysqlServiceMigration,
    RabbitMQServiceMigration,
    EgressGatewayMigration,
]

# 第三方应用迁移步骤
THIRD_APP_MIGRATION_CLASSES_LIST = [
    BaseObjectMigration,
    MainInfoMigration,
    ProductMigration,
    MarketMigration,
]
