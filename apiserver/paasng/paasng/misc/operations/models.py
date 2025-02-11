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

from django.db import models
from jsonfield import JSONField

from paasng.platform.applications.models import Application
from paasng.utils.models import BkUserField


class Operation(models.Model):
    """[deprecated] 请不要再使用 misc.operations 目录下的任何内容，暂时保留仅用于社区版本将存量的操作记录同步到 misc.audit 中

    release-1.6 版本已经将操作记录迁移到 misc.audit 中，并在 misc.audit.migrations.0002_transfer_op 将原有的操作记录迁移到 audit 表中。

    TODO 在 release-1.8 版本完全删除 misc.operations 目录下所有内容
    """

    region = models.CharField(max_length=32, help_text="部署区域")
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    user = BkUserField()
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, help_text="操作的PAAS应用", null=True, blank=True
    )
    type = models.SmallIntegerField(help_text="操作类型", db_index=True)
    is_hidden = models.BooleanField(default=False, help_text="隐藏起来")  # 同一事件最终只展示一条记录
    source_object_id = models.CharField(
        default="", null=True, blank=True, max_length=32, help_text="事件来源对象ID，具体指向需要根据操作类型解析"
    )
    # 只记录 module_name，保证 module 删除时相关记录仍旧存在
    module_name = models.CharField(null=True, verbose_name="关联 Module", max_length=20)
    extra_values = JSONField(default={}, help_text="操作额外信息", blank=True)
