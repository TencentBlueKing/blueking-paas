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
from typing import List

from paasng.bk_plugins.pluginscenter.constants import PluginReleaseStatus, PluginRevisionType
from paasng.bk_plugins.pluginscenter.models import PluginInstance
from paasng.bk_plugins.pluginscenter.sourcectl import get_plugin_repo_accessor
from paasng.bk_plugins.pluginscenter.sourcectl.base import AlternativeVersion


def get_source_hash_by_plugin_version(
    plugin: PluginInstance, version_type: str, version_name: str, revision_type: str, release_id: str
) -> str:
    if revision_type == PluginRevisionType.TESTED_VERSION:
        return plugin.test_versions.get(id=release_id).source_hash
    return get_plugin_repo_accessor(plugin).extract_smart_revision(f"{version_type}:{version_name}")


def get_testd_versions(plugin: PluginInstance, revision_type: str) -> List[AlternativeVersion]:
    result = []
    # 获取所有已经测试成功的版本
    tested_release_list = plugin.test_versions.filter(status=PluginReleaseStatus.SUCCESSFUL).order_by("-updated")
    for release in tested_release_list:
        result.append(
            AlternativeVersion(
                name=release.version,
                type=revision_type,
                revision=release.source_hash,
                last_update=release.updated,
                url=f"release_id={release.id}",
                extra={"release_id": release.id},
            )
        )
    return result
