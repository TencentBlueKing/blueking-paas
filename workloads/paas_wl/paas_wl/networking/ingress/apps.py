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
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class IngressConfig(AppConfig):
    name = 'paas_wl.networking.ingress'
    # 模块原来的名字是 "services", 架构调整后重命名为 "ingress"
    # 由于涉及 django App 名称修改, 会影响到 django_migrations 表记录的迁移执行情况, 需要配合 migrations.replaces 进行限制
    label = 'ingress'

    def ready(self):
        from .plugins.ingress import register

        register()
