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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class TemplateType(StrStructuredEnum):
    """模板类型"""

    NORMAL = EnumField("normal", _("普通应用"))
    PLUGIN = EnumField("plugin", _("插件模板"))


class RenderMethod(StrStructuredEnum):
    """模板渲染方式

    - cookiecutter: 使用 Cookiecutter 模板系统进行渲染，支持目录结构生成和复杂交互，目前插件都使用该方式
    - django_template: 使用 Django 模板引擎进行渲染，支持变量替换和简单逻辑，目前开发框架都使用该方式
    - jinja2_double_square_bracket: 使用 Jinja2 模板引擎进行渲染，通过 [[ ]] 匹配渲染点，新版 Golang 框架需使用该方式
    """

    COOKIECUTTER = EnumField("cookiecutter")
    DJANGO_TEMPLATE = EnumField("django_template")
    JINJA2_DOUBLE_SQUARE_BRACKET = EnumField("jinja2_double_square_bracket")
