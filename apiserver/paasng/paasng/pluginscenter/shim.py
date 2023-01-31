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
import logging

from django.utils.translation import gettext_lazy as _

from paasng.dev_resources.sourcectl.git.client import GitCommandExecutionError
from paasng.pluginscenter import constants
from paasng.pluginscenter.exceptions import error_codes
from paasng.pluginscenter.iam_adaptor.management.shim import (
    add_role_members,
    setup_builtin_grade_manager,
    setup_builtin_user_groups,
)
from paasng.pluginscenter.models import PluginInstance, PluginMarketInfo
from paasng.pluginscenter.sourcectl import add_repo_member, get_plugin_repo_initializer
from paasng.pluginscenter.sourcectl.exceptions import APIError
from paasng.pluginscenter.thirdparty.instance import create_instance

logger = logging.getLogger(__name__)


def init_plugin_in_view(plugin: PluginInstance, operator: str):
    """初始化插件

    :param plugin: 蓝鲸插件
    :param operator: 用户名
    """
    # 初始化插件仓库后, plugin.repository 才真正赋值
    if plugin.pd.basic_info_definition.release_method == constants.PluginReleaseMethod.CODE:
        init_plugin_repository(plugin, operator)

    # 调用第三方系统API时, 必须保证 plugin.repository 不为空
    if plugin.pd.basic_info_definition.api.create:
        try:
            create_instance(plugin.pd, plugin, operator)
        except Exception:
            logger.exception("同步插件信息至第三方系统失败, 请联系相应的平台管理员排查")
            raise error_codes.THIRD_PARTY_API_ERROR

    # 创建默认市场信息
    PluginMarketInfo.objects.create(plugin=plugin, extra_fields={})
    # 创建 IAM 分级管理员
    setup_builtin_grade_manager(plugin)
    # 创建 IAM 用户组
    setup_builtin_user_groups(plugin)
    # 添加默认管理员
    add_role_members(plugin, role=constants.PluginRole.ADMINISTRATOR, usernames=[operator])


def init_plugin_repository(plugin: PluginInstance, operator: str):
    """初始化插件仓库"""
    initializer = get_plugin_repo_initializer(plugin.pd)
    try:
        initializer.create_project(plugin)
    except APIError as e:
        if e.message == '400 bad request for {:path=>["Path has already been taken"]}':
            raise error_codes.CREATE_REPO_ERROR.f(_("同名仓库已存在"))
        logger.exception("创建仓库返回异常, 异常信息: %s", e.message)
        raise error_codes.CREATE_REPO_ERROR

    try:
        initializer.initial_repo(plugin)
    except GitCommandExecutionError:
        logger.exception("执行 git 指令异常, 请联系管理员排查")
        raise error_codes.INITIAL_REPO_ERROR

    add_repo_member(plugin, operator, role=constants.PluginRole.ADMINISTRATOR)


def build_repository_template(repository_group: str) -> str:
    """transfer a repository group to repository template"""
    if not repository_group.endswith("/"):
        repository_group += "/"
    return repository_group + "{{ plugin_id }}.git"
