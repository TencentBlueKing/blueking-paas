# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""Project 与远端 Git 仓库的一对一关联。"""

from blue_krill.models.fields import EncryptField
from django.db import models

from app_spark_api.repository.git.constants import DEFAULT_BRANCH, STATUS_PENDING
from app_spark_api.utils.models import TimestampedModel


class ProjectGitRepository(TimestampedModel):
    """One private Git repository for one Project, plus the long-lived write token."""

    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="git_repository",
    )
    remote_id = models.BigIntegerField(null=True, blank=True, help_text="远端仓库数字 ID")
    owner = models.CharField(max_length=64, help_text="远端组织名")
    name = models.CharField(max_length=64, help_text="远端仓库名，与 Project ID 相同")
    default_branch = models.CharField(max_length=64, default=DEFAULT_BRANCH)
    status = models.CharField(max_length=16, default=STATUS_PENDING)
    status_detail = models.TextField(blank=True, default="")
    write_token = EncryptField(null=True, blank=True, help_text="仓库范围的读写 token 明文（加密存储）")
    write_token_id = models.PositiveIntegerField(null=True, blank=True, help_text="远端 token ID，用于撤销")
    clone_url = models.CharField(max_length=512, blank=True, default="")
