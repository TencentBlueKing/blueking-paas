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

from blue_krill.models.fields import EncryptField
from django.db import models
from django.utils.translation import gettext_lazy as _

from paas_wl.utils.models import AuditedModel
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.platform.modules.models import Module


class PresetEnvVariable(AuditedModel):
    """应用描述文件中预定义的环境变量"""

    module = models.ForeignKey(Module, on_delete=models.CASCADE, db_constraint=False)
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=ConfigVarEnvName.get_choices(), max_length=16
    )
    key = models.CharField(max_length=128, null=False)
    value = EncryptField(null=False)
    description = models.CharField(verbose_name=_("变量描述"), max_length=200, blank=True, null=True)

    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("module", "environment_name", "key")

    def is_within_scope(self, given_env: ConfigVarEnvName) -> bool:
        """判断当前的环境变量在所给的环境中是否生效"""
        if self.environment_name is None or self.environment_name == ConfigVarEnvName.GLOBAL:
            return True
        return self.environment_name == given_env
