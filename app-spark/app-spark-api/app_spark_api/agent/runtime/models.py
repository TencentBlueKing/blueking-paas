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

"""Durable inventory of E2B sandboxes created by the API service."""

from __future__ import annotations

from blue_krill.models.fields import EncryptField
from django.db import models

from app_spark_api.utils.models import TimestampedModel


class E2BSandboxRecordManager(models.Manager["E2BSandboxRecord"]):
    """Queries for the sandboxes that still own a conversation or project."""

    def active_for_conversation(self, conversation_id: str) -> models.QuerySet[E2BSandboxRecord]:
        """Find the active sandbox assigned to a conversation.

        :param conversation_id: Runtime conversation identity.
        :return: A queryset containing at most one active record.
        """
        return self.filter(active_conversation_id=conversation_id)

    def active_for_project(self, project_id: str) -> models.QuerySet[E2BSandboxRecord]:
        """Find the active sandbox occupying a project's workspace.

        :param project_id: Project identity.
        :return: A queryset containing at most one active record.
        """
        return self.filter(active_project_id=project_id)

    def active(self) -> models.QuerySet[E2BSandboxRecord]:
        """Find all sandboxes not yet released by the provider.

        :return: Active sandbox records.
        """
        return self.filter(active_conversation_id__isnull=False)


class E2BSandboxRecord(TimestampedModel):
    """One claim on an E2B sandbox for a conversation, from reservation to its eventual end.

    The record is written *before* its sandbox exists. Claiming the unique active IDs first means
    only the request that won them ever asks E2B for a sandbox, so a lost race costs nothing to
    clean up. A record therefore moves through three states:

    * claimed -- active IDs set, ``sandbox_id`` still empty while E2B creates the sandbox;
    * bound -- ``sandbox_id`` and the connection metadata filled in, the sandbox is serving;
    * released -- active IDs cleared and ``stopped_at`` set. A claim released before it was ever
      bound is the history of a provisioning attempt that produced no sandbox.

    Original IDs retain ownership history after termination. Nullable unique active IDs enforce
    one sandbox per conversation and project while it runs, including on MySQL, where partial
    unique indexes cannot provide this constraint. Releasing a sandbox clears only its active IDs.
    """

    # Business identity and ownership. The runtime token authenticates the Agent HTTP API;
    # original IDs remain for history, while unique active IDs reserve live workspaces. The
    # sandbox ID is not the primary key because E2B only assigns it after the claim is made.
    sandbox_id = models.CharField(verbose_name="E2B 沙箱 ID", max_length=128, unique=True, null=True)
    project_id = models.CharField(verbose_name="原始项目 ID", max_length=128, db_index=True)
    conversation_id = models.CharField(verbose_name="原始会话 ID", max_length=128, db_index=True)
    active_project_id = models.CharField(verbose_name="占用中的项目 ID", max_length=128, unique=True, null=True)
    active_conversation_id = models.CharField(verbose_name="占用中的会话 ID", max_length=128, unique=True, null=True)
    runtime_token = EncryptField(verbose_name="Agent Runtime 访问令牌")

    # Creation history; the template is recorded for inspection, not used to reconnect.
    template = models.CharField(verbose_name="沙箱模板", max_length=128)

    # SDK connection metadata, filled in when the claim is bound. Preview requests address the
    # sandbox from these alone, and a restarted worker uses them when the self-hosted control
    # plane cannot reconnect a still-running sandbox; they do not determine business ownership.
    sandbox_domain = models.CharField(verbose_name="沙箱访问域名", max_length=255, null=True)
    envd_version = models.CharField(verbose_name="沙箱 envd 版本", max_length=64, null=True)
    sandbox_headers = EncryptField(verbose_name="沙箱连接头", default="{}")
    traffic_access_token = EncryptField(verbose_name="端口代理访问令牌", null=True)

    # Lifecycle history remains after active ownership has been released. Supported reasons:
    # ``terminated`` (stopped on request), ``expired`` (found gone), ``failed`` (provisioning
    # raised), ``abandoned`` (a claim whose worker never came back to bind it).
    stopped_at = models.DateTimeField(verbose_name="停止或失效时间", null=True, default=None)
    stop_reason = models.CharField(verbose_name="停止原因", max_length=32, blank=True, default="")

    objects = E2BSandboxRecordManager()

    class Meta:
        indexes = [models.Index(fields=["conversation_id", "-created_at"])]

    @property
    def is_bound(self) -> bool:
        """Whether E2B has created the sandbox this record claimed."""
        return self.sandbox_id is not None
