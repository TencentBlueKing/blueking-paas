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
from typing import List

from paasng.platform.engine.models.config_var import BuiltInEnvVarDetail

from .models import get_region


class AppRegionHelper:
    """AppRegionHelper is a helper for connect Application and region"""

    def __init__(self, application):
        self.application = application
        self.region = get_region(self.application.region)


class BuiltInEnvsRegionHelper:
    """Helps getting env vars from region configs, for example:

    If a region has below configs:

    ```
    "built_in_config_var": {
        "FOO": {
            "stag": "bar_stag",
            "prod": "bar_prod"
        }
    }
    ```

    For application under this region, its stag environment will has an environment variable named
    "FOO" whose value was set to "bar_stag". While in prod environment, the value is "bar_prod".
    """

    def __init__(self, region_name, app_env, prefix, required_env_dict):
        """
        :param app_env: application environment, such as stag,prod
        :param prefix: environment variable prefix
        :param required_env_dict: required environment variables, including key descriptions, need to be supplemented with corresponding values
        """
        self.region = get_region(region_name)
        self.app_env = app_env
        self.prefix = prefix
        self.required_env_dict = required_env_dict

    def get_envs(self) -> List[BuiltInEnvVarDetail]:
        result = []
        for key in self.required_env_dict:
            value = self.region.get_built_in_config_var(key=key, env=self.app_env)
            if value:
                result.append(
                    BuiltInEnvVarDetail(
                        key=key,
                        prefix=self.prefix,
                        value=value,
                        description=self.required_env_dict[key]["description"],
                    )
                )
        return result


class S3BucketRegionHelper:
    def __init__(self, application):
        self.application = application
        self.region = get_region(self.application.region)

    def get_logo_bucket(self):
        return self.region.basic_info.get_logo_bucket_name()
