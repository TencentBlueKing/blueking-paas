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


import copy
from typing import Any, Dict

from django.conf import settings


class SourceConfigTemplateManager:
    """代码库配置模板管理器"""

    def __init__(self):
        self._templates = self._get_default_templates()

    def get_all_templates(self) -> Dict[str, Any]:
        """获取所有配置模板"""
        return copy.deepcopy(self._templates)

    def get_template(self, name: str) -> Dict[str, Any]:
        """获取指定配置模板"""
        return copy.deepcopy(self._templates.get(name, {}))

    def _get_default_templates(self):
        return {
            "github": self._build_github_template(),
            "gitee": self._build_gitee_template(),
        }

    def _build_github_template(self) -> Dict[str, Any]:
        """构建 GitHub 配置模板"""
        return {
            "name": "github",
            "label_zh_cn": "Github",
            "label_en": "Github",
            "spec_cls": "GitHubSourceTypeSpec",
            "server_config": {"api_url": "https://api.github.com/"},
            "display_info_zh_cn": {"name": "Github", "description": "开源社区"},
            "display_info_en": {"name": "Github", "description": "OpenSource Community"},
            "authorization_base_url": "https://github.com/login/oauth/authorize",
            "client_id": "",
            "client_secret": "",
            "redirect_uri": f"{settings.BKPAAS_URL}/backend/api/oauth/complete/github",
            "token_base_url": "https://github.com/login/oauth/access_token",
            "oauth_display_info_zh_cn": {
                "auth_docs": f"{settings.PAAS_DOCS_URL_PREFIX}/BaseGuide/topics/paas/github_oauth"
            },
            "oauth_display_info_en": {
                "auth_docs": f"{settings.PAAS_DOCS_URL_PREFIX}/BaseGuide/topics/paas/github_oauth"
            },
        }

    def _build_gitee_template(self) -> Dict[str, Any]:
        """构建 Gitee 配置模板"""
        return {
            "name": "gitee",
            "label_zh_cn": "Gitee",
            "label_en": "Gitee",
            "spec_cls": "GiteeSourceTypeSpec",
            "server_config": {"api_url": "https://gitee.com/api/v5/"},
            "display_info_zh_cn": {"name": "Gitee", "description": "开源社区"},
            "display_info_en": {"name": "Gitee", "description": "OpenSource Community"},
            "authorization_base_url": "https://gitee.com/oauth/authorize",
            "client_id": "",
            "client_secret": "",
            "redirect_uri": f"{settings.BKPAAS_URL}/backend/api/oauth/complete/gitee",
            "token_base_url": "https://gitee.com/oauth/token",
            "oauth_display_info_zh_cn": {
                "auth_docs": f"{settings.PAAS_DOCS_URL_PREFIX}/BaseGuide/topics/paas/gitee_oauth"
            },
            "oauth_display_info_en": {
                "auth_docs": f"{settings.PAAS_DOCS_URL_PREFIX}/BaseGuide/topics/paas/gitee_oauth"
            },
        }


# 全局实例
source_config_tpl_manager = SourceConfigTemplateManager()
