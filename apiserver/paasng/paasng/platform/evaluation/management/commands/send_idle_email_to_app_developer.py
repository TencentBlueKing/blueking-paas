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

"""Send idle email to application developers

Examples:

    # 仅通知指定的应用的管理员 & 开发者
    python manage.py send_idle_email_to_app_developer --codes app-code-1 app-code-2

    # 全量应用通知
    python manage.py send_idle_email_to_app_developer --all

    # 全量应用 + 异步执行
    python manage.py send_idle_email_to_app_developer --all --async

    # 通知时候排除特定的人员
    python manage.py send_idle_email_to_app_developer --all --exclude_specified_users user-1 user-2

    # 仅通知指定的应用的指定管理员 & 开发者
    python manage.py send_idle_email_to_app_developer --codes app-code-1 --only_specified_users user-1 user-2
"""

from django.core.management.base import BaseCommand

from paasng.platform.evaluation.tasks import send_idle_email_to_app_developers


class Command(BaseCommand):
    help = "Send application's idle module env infos to application's developers by emails"

    def add_arguments(self, parser):
        parser.add_argument("--tenant_id", dest="tenant_id", required=True, help="The tenant ID")
        parser.add_argument("--codes", dest="app_codes", default=[], nargs="*", help="应用 Code 列表")
        parser.add_argument(
            "--only_specified_users", dest="only_specified_users", default=[], nargs="*", help="只发送给指定的用户"
        )
        parser.add_argument(
            "--exclude_specified_users", dest="exclude_specified_users", default=[], nargs="*", help="排除指定的用户"
        )
        parser.add_argument("--all", dest="notify_all", default=False, action="store_true", help="全量应用通知")
        parser.add_argument("--async", dest="async_run", default=False, action="store_true", help="异步执行")

    def handle(
        self,
        tenant_id,
        app_codes,
        only_specified_users,
        exclude_specified_users,
        notify_all,
        async_run,
        *args,
        **options,
    ):
        if not (notify_all or app_codes):
            raise ValueError("please specify --codes or --all")

        if async_run:
            send_idle_email_to_app_developers.delay(
                tenant_id, app_codes, only_specified_users, exclude_specified_users
            )
        else:
            send_idle_email_to_app_developers(tenant_id, app_codes, only_specified_users, exclude_specified_users)
