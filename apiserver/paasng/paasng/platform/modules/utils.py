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

from django.conf import settings

from paasng.infras.oauth2.utils import get_oauth2_client_secret
from paasng.platform.modules.models import Module
from paasng.platform.templates.constants import TemplateType
from paasng.utils.basic import get_username_by_bkpaas_user_id


def parse_assignment_list(assignments):
    """
    Parse assignment expression list, for example:
    input: ["a=b"]
    return: {"a": "b"}
    """
    return dict(i.split("=", 1) for i in assignments)


def get_module_init_repo_context(module: Module, template_type: TemplateType):
    """获取模块初始化代码仓库的上下文
    NOTE: 插件应用的渲染字段名是由插件中心统一定义，变量名与开发框架中定义的不一致，故需要根据模板类型生成不同的上下文
    """
    application = module.application

    client_secret = get_oauth2_client_secret(application.code)
    owner_username = get_username_by_bkpaas_user_id(application.owner)

    if template_type == TemplateType.PLUGIN:
        # 插件模板专用字段
        return {
            "project_name": application.code,
            "plugin_desc": application.name,
            "init_admin": owner_username,
            "init_apigw_maintainer": owner_username,
            "apigw_manager_url_tmpl": settings.BK_API_URL_TMPL,
        }
    # 普通模板字段
    return {
        "region": application.region,
        "owner_username": owner_username,
        "app_code": application.code,
        "app_secret": client_secret,
        "app_name": application.name,
        "BK_URL": settings.COMPONENT_SYSTEM_HOST_IN_TEST,
        "BK_LOGIN_URL": settings.LOGIN_FULL,
    }
