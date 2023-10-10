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
from django.conf import settings

from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.models import PluginDefinition, PluginInstance
from paasng.bk_plugins.pluginscenter.sourcectl.base import (
    AlternativeVersion,
    PluginRepoAccessor,
    PluginRepoInitializer,
    PluginRepoMemberMaintainer,
)
from paasng.bk_plugins.pluginscenter.sourcectl.tencent import PluginRepoAccessor as TencentPluginRepoAccessor
from paasng.bk_plugins.pluginscenter.sourcectl.tencent import PluginRepoInitializer as TencentPluginRepoInitializer
from paasng.bk_plugins.pluginscenter.sourcectl.tencent import (
    PluginRepoMemberMaintainer as TencentPluginRepoMemberMaintainer,
)


def get_plugin_repo_initializer(pd: PluginDefinition) -> PluginRepoInitializer:
    conf = settings.PLUGIN_REPO_CONF
    user_credentials = {"private_token": conf["private_token"]}
    return TencentPluginRepoInitializer(pd=pd, api_url=conf["api_url"], user_credentials=user_credentials)


def get_plugin_repo_accessor(plugin: PluginInstance) -> PluginRepoAccessor:
    conf = settings.PLUGIN_REPO_CONF
    user_credentials = {"private_token": conf["private_token"]}
    return TencentPluginRepoAccessor(plugin=plugin, api_url=conf["api_url"], user_credentials=user_credentials)


def get_plugin_repo_member_maintainer(plugin: PluginInstance) -> PluginRepoMemberMaintainer:
    conf = settings.PLUGIN_REPO_CONF
    user_credentials = {"private_token": conf["private_token"]}
    return TencentPluginRepoMemberMaintainer(plugin=plugin, api_url=conf["api_url"], user_credentials=user_credentials)


def build_master_placeholder() -> AlternativeVersion:
    return AlternativeVersion(name="master", type="branch", revision="nonsense", url="")


def add_repo_member(plugin: PluginInstance, username: str, role: PluginRole):
    """A shortcut to add member to repo and transform all exception to APIError"""
    try:
        get_plugin_repo_member_maintainer(plugin).add_member(username, role)
    except Exception:
        raise error_codes.MAINTAIN_REPO_MEMBERS_ERROR


def remove_repo_member(plugin: PluginInstance, username: str):
    """A shortcut to remove member of repo and transform all exception to APIError"""
    try:
        get_plugin_repo_member_maintainer(plugin).remove_member(username)
    except Exception:
        raise error_codes.MAINTAIN_REPO_MEMBERS_ERROR
