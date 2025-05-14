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

import logging

from django.db import models

from paasng.bk_plugins.pluginscenter.constants import PluginRole
from paasng.bk_plugins.pluginscenter.models import PluginInstance
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.utils.models import AuditedModel

logger = logging.getLogger(__name__)


class PluginRelativeManager(models.Manager):
    def filter_by_plugin(self, plugin: PluginInstance):
        return self.filter(pd_id=plugin.pd.identifier, plugin_id=plugin.id)


class PluginGradeManager(AuditedModel):
    """
    IAM 分级管理员与插件的关系

    分级管理员管理用户加入用户组的申请，理论上来说，某个应用的分级管理员与管理者的成员是一致的

    [multi-tenancy] This model is not tenant-aware.
    """

    pd_id = models.CharField(help_text="插件类型标识", max_length=64)
    plugin_id = models.CharField(help_text="插件标识", max_length=32)
    grade_manager_id = models.IntegerField(help_text="分级管理员 ID")
    tenant_id = tenant_id_field_factory()

    objects = PluginRelativeManager()

    class Meta:
        unique_together = ("pd_id", "plugin_id", "grade_manager_id")


class PluginUserGroup(AuditedModel):
    """
    IAM 用户组与插件开发中心用户组的关系

    每个插件默认会有 2 个用户组（不可删除）：管理者，开发者

    [multi-tenancy] This model is not tenant-aware.
    """

    pd_id = models.CharField(help_text="插件类型标识", max_length=64)
    plugin_id = models.CharField(help_text="插件标识", max_length=32)
    role = models.IntegerField(default=PluginRole.DEVELOPER.value)
    user_group_id = models.IntegerField(help_text="权限中心用户组 ID")
    tenant_id = tenant_id_field_factory()

    objects = PluginRelativeManager()

    class Meta:
        unique_together = ("pd_id", "plugin_id", "role")
