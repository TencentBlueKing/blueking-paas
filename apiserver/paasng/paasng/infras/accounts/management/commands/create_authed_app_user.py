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

"""Add a database user and allow it to be authenticated by a verified application,
see `AuthenticatedAppAsClientMiddleware` for more details

IMPORTANT: This command should have been renamed to create_authed_app_client after we migrated
the authentication mechanism to the sysapi client, but the original name was retained for compatibility reasons.
"""

import logging

from django.core.management.base import BaseCommand

from paasng.infras.sysapi_client.constants import ClientRole
from paasng.infras.sysapi_client.models import AuthenticatedAppAsClient, SysAPIClient

logger = logging.getLogger("commands")

ROLE_CHOICES = [
    ClientRole.BASIC_READER.value,
    ClientRole.BASIC_MAINTAINER.value,
    ClientRole.LIGHT_APP_MAINTAINER.value,
    ClientRole.LESSCODE.value,
]


class Command(BaseCommand):
    help = (
        "Add an user which can be authenticated an by verified apps, overwrite old records when "
        "bk_app_code already exists"
    )

    def add_arguments(self, parser):
        parser.add_argument("--bk_app_code", required=True, type=str, help="application code")
        parser.add_argument(
            "--username",
            required=False,
            type=str,
            help="username, if not given use '{bk-app-code}-sys-user' by default",
        )
        parser.add_argument(
            "--role",
            required=False,
            type=int,
            choices=ROLE_CHOICES,
            default=ClientRole.BASIC_READER.value,
            help=(
                'User role, choices: 50 - "basic reader"(default); '
                '60 - "basic maintainer"; 70 - "light app maintainer".'
            ),
        )

    def handle(self, *args, **options):
        bk_app_code = options["bk_app_code"]
        username = options["username"] or self._get_default_username(bk_app_code)
        # Create the client
        client, _ = SysAPIClient.objects.get_or_create(name=username, defaults={"role": options["role"]})
        logger.info(f"user: {client.name} created.")

        # Create relationship
        AuthenticatedAppAsClient.objects.update_or_create(
            bk_app_code=bk_app_code, defaults={"client": client, "is_active": True}
        )
        logger.info(f"app-user relation: {bk_app_code}-{client.name} created.")

    @staticmethod
    def _get_default_username(bk_app_code: str) -> str:
        return f"authed-app-{bk_app_code}"
