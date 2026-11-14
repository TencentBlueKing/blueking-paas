# -*- coding: utf-8 -*-
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

"""下发记录由真实的下发流程产生，再验证据此得出的状态"""

import pytest

from paas_wl.infras.cluster.models import ClusterE2BConfig
from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateStatus, E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.template_sync import status, sync
from tests.paasng.platform.agent_sandbox.e2b.helpers import make_builtin_template, make_custom_template
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .fakes import OTHER_CLUSTER, image_of, status_of

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestOverviews:
    def test_template_status_follows_worst_cluster(self, clusters):
        template = make_builtin_template("e2b-envd")
        sync.mark_pending(template)

        def _status():
            refreshed = type(template).objects.prefetch_related("sync_records").get(pk=template.pk)
            return status.get_template_overviews([refreshed])[0].status

        assert _status() == E2BTemplateSyncStatus.PENDING.value

        clusters.broken_clusters.add(OTHER_CLUSTER)
        sync.sync_template("e2b-envd")
        assert _status() == E2BTemplateSyncStatus.FAILED.value

        clusters.broken_clusters.clear()
        sync.sync_template("e2b-envd")
        assert _status() == E2BTemplateSyncStatus.SUCCEEDED.value

    def test_template_without_target_cluster(self, bk_app):
        ClusterE2BConfig.objects.update(enabled=False)
        template = make_custom_template(bk_app, "mine")

        (overview,) = status.get_template_overviews([template])

        assert (overview.status, overview.records, overview.missing) == (None, [], [])


class TestTemplateStatuses:
    """测试租户的首选集群是 CLUSTER_NAME_FOR_TESTING，OTHER_CLUSTER 不在它的分配策略里"""

    @staticmethod
    def _status(app, template) -> E2BTemplateStatus:
        template = type(template).objects.get(pk=template.pk)
        return status.get_template_statuses(app, [template])[template.resource_name]

    def test_available_once_applied(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        sync.mark_pending(template)
        assert self._status(bk_app, template) == E2BTemplateStatus.SYNCING

        sync.sync_template(template.resource_name)

        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_changed_spec_is_syncing_until_applied(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        sync.sync_template(template.resource_name)

        template.image = "new:v2"
        template.save()
        sync.mark_pending(template)
        assert self._status(bk_app, template) == E2BTemplateStatus.SYNCING

        sync.sync_template(template.resource_name)
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_non_spec_change_keeps_available(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        sync.sync_template(template.resource_name)

        type(template).objects.filter(pk=template.pk).update(name="renamed", description="changed")

        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_available_during_resync_until_it_fails(self, clusters, bk_app):
        """运维重新同步期间照常可用；只看最近一次下发，重新同步失败了也不再可用"""
        template = make_custom_template(bk_app, "mine")
        sync.sync_template(template.resource_name)

        sync.mark_sync_pending()
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

        clusters.broken_clusters.add(CLUSTER_NAME_FOR_TESTING)
        sync.sync_all()
        assert self._status(bk_app, template) == E2BTemplateStatus.SYNC_FAILED

    def test_partial_push_then_revert_is_not_available(self, clusters, bk_app):
        """模板已写入、池子失败时，集群里已是新配置；改回旧配置后不能凭更早的成功判为可用"""
        template = make_custom_template(bk_app, "mine", image="old:v1")
        sync.sync_template(template.resource_name)
        template.image = "new:v2"
        template.save()
        clusters.failing_pools.add(template.resource_name)
        sync.sync_template(template.resource_name)
        assert image_of(clusters, CLUSTER_NAME_FOR_TESTING, template.resource_name) == "new:v2"

        template.image = "old:v1"
        template.save()
        sync.mark_pending(template)

        assert self._status(bk_app, template) == E2BTemplateStatus.SYNCING
        assert not status.is_applied(template, CLUSTER_NAME_FOR_TESTING)

        clusters.failing_pools.clear()
        sync.sync_template(template.resource_name)
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_failed_push_of_current_spec(self, clusters, bk_app):
        template = make_custom_template(bk_app, "mine")
        clusters.failing_names.add(template.resource_name)

        sync.sync_template(template.resource_name)

        assert self._status(bk_app, template) == E2BTemplateStatus.SYNC_FAILED

    def test_only_preferred_cluster_matters(self, clusters, bk_app):
        template = make_builtin_template("e2b-envd")
        clusters.broken_clusters.add(OTHER_CLUSTER)

        sync.sync_template("e2b-envd")

        assert status_of(template)[OTHER_CLUSTER] == E2BTemplateSyncStatus.FAILED.value
        assert self._status(bk_app, template) == E2BTemplateStatus.AVAILABLE

    def test_digest_follows_what_was_pushed(self, clusters, bk_app, race_after_first_apply):
        """下发途中模板又被修改：记录是成功，但集群里是修改前的配置，仍要等下一次下发"""
        template = make_custom_template(bk_app, "mine", image="old:v1")
        race_after_first_apply(lambda: type(template).objects.filter(pk=template.pk).update(image="new:v2"))

        sync.sync_template(template.resource_name)

        assert status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}
        assert self._status(bk_app, template) == E2BTemplateStatus.SYNCING

    def test_no_cluster(self, bk_app):
        ClusterE2BConfig.objects.update(enabled=False)
        template = make_custom_template(bk_app, "mine")

        assert self._status(bk_app, template) == E2BTemplateStatus.NO_CLUSTER
