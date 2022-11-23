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
from django.db import models


class RepoQuotaStatistics(models.Model):
    instance = models.ForeignKey("paas_service.ServiceInstance", on_delete=models.CASCADE, db_constraint=False)
    repo_name = models.CharField(max_length=64, verbose_name="仓库名称")
    max_size = models.BigIntegerField(verbose_name="仓库最大配额", null=True, help_text="单位字节，值为 nul 时表示未设置仓库配额")
    used = models.BigIntegerField(verbose_name="仓库已使用容量", default=0, help_text="单位字节")
    updated = models.DateTimeField(auto_now=True)

    @property
    def quota_used_rate(self) -> float:
        """配额使用率(%)"""
        if self.max_size is None:
            # 如果不限制仓库配额, 则使用率为 0
            return 0
        return self.used / self.max_size * 100
