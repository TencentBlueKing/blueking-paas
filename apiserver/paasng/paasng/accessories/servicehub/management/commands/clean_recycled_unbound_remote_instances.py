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

from paasng.accessories.servicehub.tasks import clean_recycled_unbound_remote_instances

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check if unbound remote service instance is recycled, if it is recycled, delete object in database."

    def handle(self, *args, **options):
        logger.info("Start to check if remote unbound service instance recycled")
        clean_recycled_unbound_remote_instances()
        logger.info("Complete check if remote unbound service instance recycled")
