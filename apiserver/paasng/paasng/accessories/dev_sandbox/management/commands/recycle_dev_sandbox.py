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

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "更新沙箱状态，并且回收不活跃的沙箱"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app_code",
            dest="app_code",
            default="",
            help="name of the model for encryption migration",
        )

        parser.add_argument(
            "--module_name",
            dest="module_name",
            default="",
            help="name of the model for encryption migration",
        )
