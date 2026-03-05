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

"""
A command for upserting built-in environment variables (BuiltinConfigVar).
"""

from bkpaas_auth import get_user_by_user_id
from bkpaas_auth.models import user_id_encoder
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from paasng.plat_mgt.config_vars.constants import CustomBuiltinConfigVarPrefix
from paasng.platform.engine.models.config_var import BuiltinConfigVar
from paasng.utils.validators import RE_CONFIG_VAR_KEY


class Command(BaseCommand):
    """添加或更新内置环境变量"""

    help = "Upsert a built-in environment variable (BuiltinConfigVar)"

    def add_arguments(self, parser):
        parser.add_argument("--key", dest="key", required=True, help="环境变量名")
        parser.add_argument("--value", dest="value", required=True, help="环境变量值")
        parser.add_argument("--description", dest="description", default="", help="环境变量描述")

    def handle(self, key, value, description, *args, **options):
        operator = get_user_by_user_id(user_id_encoder.encode(settings.USER_TYPE, settings.ADMIN_USERNAME))

        # Note: The key validation logic below is aligned with BuiltinConfigVarCreateInputSLZ.
        # Keep them in sync if the validation rules change.
        if not RE_CONFIG_VAR_KEY.match(key):
            raise CommandError(
                f"Invalid key format: '{key}'. Key must start with an uppercase letter and consist of "
                "uppercase letters, digits, and underscores only."
            )
        valid_prefixes = CustomBuiltinConfigVarPrefix.get_values()
        if not key.startswith(tuple(valid_prefixes)):
            raise CommandError(
                f"Invalid key prefix for '{key}'. Key must start with one of: {', '.join(valid_prefixes)}"
            )

        _, created = BuiltinConfigVar.objects.update_or_create(
            key=key,
            defaults={"value": value, "description": description, "operator": operator},
        )
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Successfully {action} built-in environment variable '{key}'."))
