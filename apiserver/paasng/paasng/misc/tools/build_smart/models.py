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

import uuid

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.db import models
from django.utils.translation import gettext as _

from paasng.utils.models import BkUserField


class SourceCodeOriginType(StrStructuredEnum):
    """源代码来源类型"""

    PACKAGE = EnumField("package", label=_("源码包"))
    REPO = EnumField("repo", label=_("代码仓库"))


class SmartBuildRecord(models.Model):
    """s-mart 包构建记录"""

    id = models.UUIDField(
        "UUID",
        default=uuid.uuid4,
        primary_key=True,
        editable=False,
        auto_created=True,
        unique=True,
    )
    source_origin = models.CharField(
        max_length=32,
        choices=SourceCodeOriginType.get_choices(),
        verbose_name=_("源码来源"),
    )
    repository_address = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="源码仓库地址, 只有 source_origin 是 repo 时才有值",
    )
    repository_branch = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="源码仓库分支, 只有 source_origin 是 repo 时才有值",
    )
    package_name = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="源码包名, 只有 source_origin 是 package 时才有值",
    )
    signature = models.CharField(
        max_length=256,
        help_text="数字签名, 当 source_origin 是 package 时才有值。格式为 SHA256 哈希字符串，需进行校验。",
    )
    artifact_url = models.TextField(blank=True, default="", help_text="s-mart 构建产物地址, 用于下载")
    status = models.CharField(max_length=32, help_text="s-mart 构建任务成功与否")
    build_int_requested_at = models.DateTimeField(null=True, help_text="用户请求中断 build 的时间")
    time_spent = models.IntegerField(null=True, help_text="s-mart 构建任务整体花费的时间 (单位: 秒)")

    operator = BkUserField()

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
