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
"""Add a database user and allow it to be authenticated by a verified application,
see `AuthenticatedAppAsUserMiddleware` for more details"""
import logging

from bkpaas_auth.models import DatabaseUser
from django.core.management.base import BaseCommand

from paasng.infras.accounts.constants import SiteRole
from paasng.infras.accounts.models import AuthenticatedAppAsUser, User, UserProfile

logger = logging.getLogger("commands")

ROLE_CHOICES = [
    SiteRole.SYSTEM_API_BASIC_READER.value,
    SiteRole.SYSTEM_API_BASIC_MAINTAINER.value,
    SiteRole.SYSTEM_API_LIGHT_APP_MAINTAINER.value,
    SiteRole.SYSTEM_API_LESSCODE.value,
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
            default=SiteRole.SYSTEM_API_BASIC_READER.value,
            help=(
                'User role, choices: 50 - "basic reader"(default); '
                '60 - "basic maintainer"; 70 - "light app maintainer".'
            ),
        )

    def handle(self, *args, **options):
        bk_app_code = options["bk_app_code"]
        username = options["username"] or self._get_default_username(bk_app_code)
        # Create user
        user_db, _ = User.objects.get_or_create(username=username)
        logger.info(f"user: {user_db.username} created.")

        # Create profile with role
        user = DatabaseUser.from_db_obj(user_db)
        UserProfile.objects.update_or_create(user=user.pk, defaults={"role": options["role"]})
        logger.info(f"profile: {user.pk}({user.username}) created.")

        # Create relationship
        AuthenticatedAppAsUser.objects.update_or_create(
            bk_app_code=bk_app_code, defaults={"user": user_db, "is_active": True}
        )
        logger.info(f"app-user relation: {bk_app_code}-{user.username} created.")

    @staticmethod
    def _get_default_username(bk_app_code: str) -> str:
        return f"authed-app-{bk_app_code}"
