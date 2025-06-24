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

from django.core.management.base import BaseCommand

from paasng.accessories.publish.market.models import ApplicationExtraInfo, Product
from paasng.utils.validators import str2bool

logger = logging.getLogger("commands")


class Command(BaseCommand):
    """
    将 Product 的 tag 字段迁移到 ApplicationExtraInfo，应用 tag 信息将由 ApplicationExtraInfo 模型提供
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", default=True, type=str2bool, help="避免意外触发, 若想执行需添加该参数"
        )

    def handle(self, dry_run: bool, *args, **kwargs):
        for product in Product.objects.all():
            if not dry_run:
                ApplicationExtraInfo.objects.update_or_create(
                    application=product.application,
                    tenant_id=product.application.tenant_id,
                    defaults={"tag": product.tag},
                )
            print(f"app:{product.application.code} tag:{product.tag} 迁移至 ApplicationExtraInfo")
