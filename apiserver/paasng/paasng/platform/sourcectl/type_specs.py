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

"""Sourcectl type specifications

包含可供用户使用的“源码控制系统配置”
"""

from typing import Dict

from django.utils.translation import gettext_lazy as _

from paasng.infras.accounts.oauth.backends import GiteeBackend, GitHubBackend, GitLabBackend
from paasng.platform.sourcectl.connector import (
    ExternalBasicAuthRepoConnector,
    ExternalGitAppRepoConnector,
    IntegratedSvnAppRepoConnector,
)
from paasng.platform.sourcectl.constants import DiffFeatureType
from paasng.platform.sourcectl.controllers.bare_git import BareGitRepoController
from paasng.platform.sourcectl.controllers.bare_svn import BareSvnRepoController
from paasng.platform.sourcectl.controllers.bk_svn import SvnRepoController
from paasng.platform.sourcectl.controllers.gitee import GiteeRepoController
from paasng.platform.sourcectl.controllers.github import GitHubRepoController
from paasng.platform.sourcectl.controllers.gitlab import GitlabRepoController
from paasng.platform.sourcectl.source_types import DiffFeature, SourceTypeSpec


class BkSvnSourceTypeSpec(SourceTypeSpec):
    connector_class = IntegratedSvnAppRepoConnector
    repo_controller_class = SvnRepoController
    oauth_backend_class = None
    basic_type = "svn"
    diff_feature = DiffFeature(method=DiffFeatureType.INTERNAL, enabled=True)

    _default_label = _("蓝鲸 SVN")
    _default_display_info = {
        "name": _("蓝鲸 SVN 服务"),
        "description": _("（蓝鲸平台提供的源码托管服务）"),
    }

    def config_as_arguments(self) -> Dict:
        server_config = self.get_server_config()
        return {
            "base_url": server_config["base_url"],
            "username": server_config["su_name"],
            "password": server_config["su_pass"],
        }


class GitHubSourceTypeSpec(SourceTypeSpec):
    connector_class = ExternalGitAppRepoConnector
    repo_controller_class = GitHubRepoController
    oauth_backend_class = GitHubBackend
    basic_type = "git"

    _default_label = "GitHub"
    _default_display_info = {
        "name": _("GitHub 服务"),
        "description": _("开源社区 GitHub"),
    }


class GiteeSourceTypeSpec(SourceTypeSpec):
    connector_class = ExternalGitAppRepoConnector
    repo_controller_class = GiteeRepoController
    oauth_backend_class = GiteeBackend
    basic_type = "git"

    _default_label = "Gitee"
    _default_display_info = {
        "name": _("Gitee 服务"),
        "description": _("开源社区 Gitee"),
    }


class BareGitSourceTypeSpec(SourceTypeSpec):
    connector_class = ExternalBasicAuthRepoConnector
    repo_controller_class = BareGitRepoController
    oauth_backend_class = None
    basic_type = "git"
    diff_feature = DiffFeature(method=None, enabled=False)

    _default_label = _("Git 代码库")
    _default_display_info = {
        "name": _("Git 代码库"),
        "description": _("（需要提供账号、密码等信息）"),
    }


class BareSvnSourceTypeSpec(SourceTypeSpec):
    connector_class = ExternalBasicAuthRepoConnector
    repo_controller_class = BareSvnRepoController
    oauth_backend_class = None
    basic_type = "svn"
    diff_feature = DiffFeature(method=None, enabled=False)

    _default_label = _("SVN 代码库")
    _default_display_info = {
        "name": _("SVN 代码库"),
        "description": _("（需要提供账号、密码等信息）"),
    }


class GitLabSourceTypeSpec(SourceTypeSpec):
    connector_class = ExternalGitAppRepoConnector
    repo_controller_class = GitlabRepoController
    oauth_backend_class = GitLabBackend
    basic_type = "git"

    _default_label = "GitLab"
    _default_display_info = {
        "name": "GitLab 服务",
        "description": "GitLab 源码托管服务",
    }


try:
    from paasng.infras.accounts.oauth.backends_ext import TcGitBackend
    from paasng.platform.sourcectl.controllers.tcgit import TcGitRepoController
    from paasng.platform.sourcectl.tc_git.provisioner import TcGitRepoProvisioner

    class TcGitSourceTypeSpec(SourceTypeSpec):
        connector_class = ExternalGitAppRepoConnector
        repo_controller_class = TcGitRepoController
        repo_provisioner_class = TcGitRepoProvisioner
        oauth_backend_class = TcGitBackend
        basic_type = "git"

        _default_label = _("工蜂 Git")
        _default_display_info = {
            "name": _("腾讯工蜂服务"),
            "description": _("（腾讯内部 Git 源码托管系统）"),
        }


except ImportError:
    pass
