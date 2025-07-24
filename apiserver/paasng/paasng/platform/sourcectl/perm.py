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

"""Permission related utilities"""

from typing import Dict, List, Sequence

from paasng.infras.accounts.models import AccountFeatureFlag, User
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.source_types import get_sourcectl_type, get_sourcectl_types


class UserSourceProviders:
    """An object to manage which source providers can a user use"""

    def __init__(self, user: User):
        self.user = user

    def list_available(self) -> List[str]:
        """Get available source provider types"""
        results = []
        featureflag_sourcectl_map = {
            type_spec.make_feature_flag_field().name: name for name, type_spec in get_sourcectl_types().items()
        }

        user_flags = AccountFeatureFlag.objects.get_user_features(self.user)
        for feature_flag, enabled in user_flags.items():
            if not enabled:
                continue

            # Flags will include those were not related with source providers, such as `ENABLE_WEB_CONSOLE`.
            # So we need to catch KeyError
            try:
                str_type = featureflag_sourcectl_map[feature_flag]
                results.append(str_type)
            except KeyError:
                pass
        return results

    def list_module_available(self, module: Module) -> List[str]:
        """Get available source providers for module"""
        default_providers = self.list_available()

        # Append module's source type when it's not presents in user's available providers
        if source_obj := module.get_source_obj():
            provider_type = source_obj.get_source_type()
            if provider_type not in default_providers:
                default_providers.append(provider_type)
        return default_providers


def render_providers(providers: Sequence[str]) -> List[Dict[str, str]]:
    """Render a source provider types into a list of detailed info dict"""
    results = []
    for provider_type in providers:
        spec = get_sourcectl_type(provider_type)
        provider_info = spec.display_info._asdict()
        provider_info.update(
            {
                "auth_method": spec.connector_class.auth_method,
                "repository_group": spec.server_config.get("repository_group", ""),
                # 是否支持由平台新建代码仓库
                "repo_creation_enabled": spec.repo_provisioner_class is not None,
                # 仓库地址
                "repository_url": spec.server_config.get("repository_url", ""),
            }
        )
        results.append(provider_info)
    return results
