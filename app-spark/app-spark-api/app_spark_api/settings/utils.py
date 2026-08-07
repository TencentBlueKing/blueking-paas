# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from dynaconf.base import LazySettings


def get_database_conf(settings: LazySettings, env_var_prefix: str = "", for_tests: bool = False) -> Optional[Dict]:
    """Get a database config dict

    :param env_var_prefix: The prefix string for reading all database config keys
    :param for_tests: Whether the conf will be used for running unittests, if True,
        the database name will be prepend with a "test_" prefix.
    """

    database_name = settings.get(env_var_prefix + "DATABASE_NAME")
    if database_name:
        database_user = settings.get(env_var_prefix + "DATABASE_USER", None)
        database_password = settings.get(env_var_prefix + "DATABASE_PASSWORD", None)
        database_host = settings.get(env_var_prefix + "DATABASE_HOST", None)
        database_port = settings.get(env_var_prefix + "DATABASE_PORT", None)
        database_options = settings.get(env_var_prefix + "DATABASE_OPTIONS", {})

        result = {
            "ENGINE": "django.db.backends.mysql",
            "NAME": database_name,
            "USER": database_user,
            "PASSWORD": database_password,
            "HOST": database_host,
            "PORT": database_port,
            "OPTIONS": database_options,
        }
        # Use a test database name when running tests to avoid unexpected changes
        if for_tests:
            result["NAME"] = f"test_{result['NAME']}"
        return result
    return None
