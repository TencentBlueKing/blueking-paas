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
from functools import wraps

from blue_krill.web.std_error import APIError as StdAPIError
from django.utils.translation import gettext_lazy as _

from paasng.bk_plugins.pluginscenter import constants
from paasng.bk_plugins.pluginscenter.exceptions import error_codes
from paasng.bk_plugins.pluginscenter.iam_adaptor.management.shim import (
    add_role_members,
    setup_builtin_grade_manager,
    setup_builtin_user_groups,
)
from paasng.bk_plugins.pluginscenter.models import PluginInstance, PluginMarketInfo
from paasng.bk_plugins.pluginscenter.sourcectl import add_repo_member, get_plugin_repo_initializer
from paasng.bk_plugins.pluginscenter.sourcectl.exceptions import APIError as SourceAPIError
from paasng.bk_plugins.pluginscenter.sourcectl.exceptions import PluginRepoNameConflict
from paasng.bk_plugins.pluginscenter.thirdparty.instance import create_instance
from paasng.platform.sourcectl.git.client import GitCommandExecutionError

logger = logging.getLogger(__name__)


def _atomic_create_plugin_repository(func):
    """保证初始化插件失败后会删除插件仓库(如果仓库已创建)"""

    @wraps(func)
    def wrapped_init_plugin_in_view(plugin: PluginInstance, operator: str):
        try:
            return func(plugin, operator)
        except Exception:
            plugin.refresh_from_db()
            if plugin.repository:
                # 如果插件仓库已创建, 则删除插件仓库
                initializer = get_plugin_repo_initializer(plugin.pd)
                try:
                    logger.warning(
                        "即将删除插件<%s/%s>的源码仓库<%s>",
                        plugin.pd.identifier,
                        plugin.id,
                        plugin.repository,
                    )
                    initializer.delete_project(plugin)
                except SourceAPIError as e:
                    logger.exception("删除插件仓库<%s>失败!", plugin.repository)
                    raise error_codes.DELETE_REPO_ERROR from e
            raise

    return wrapped_init_plugin_in_view


@_atomic_create_plugin_repository
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
            api_call_success = create_instance(plugin.pd, plugin, operator)
        except StdAPIError:
            logger.exception("同步插件信息至第三方系统失败, 请联系相应的平台管理员排查")
            raise
        except Exception:
            logger.exception("同步插件信息至第三方系统失败, 请联系相应的平台管理员排查")
            raise error_codes.THIRD_PARTY_API_ERROR

        if not api_call_success:
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
    except PluginRepoNameConflict:
        raise error_codes.CREATE_REPO_ERROR.f(_("同名仓库已存在"))
    except SourceAPIError as e:
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
