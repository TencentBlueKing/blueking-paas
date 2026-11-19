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

import pytest

from paasng.platform.agent_sandbox.e2b.constants import E2BTemplateSyncStatus
from paasng.platform.agent_sandbox.e2b.template_sync import states, sync
from paasng.platform.agent_sandbox.models import E2BSandboxTemplateSyncState
from tests.paasng.platform.agent_sandbox.e2b.test_utils import make_builtin_template, make_custom_template
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .fakes import OTHER_CLUSTER, status_of

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestMarkPending:
    def test_marks_target_clusters_pending(self, bk_app):
        builtin = make_builtin_template("e2b-envd")
        custom = make_custom_template(bk_app, "mine")

        states.mark_pending(builtin)
        states.mark_pending(custom)

        assert status_of(builtin) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert status_of(custom) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value}

    def test_overwrites_previous_result(self):
        template = make_builtin_template("e2b-envd")
        E2BSandboxTemplateSyncState.objects.create(
            template=template, cluster_name=CLUSTER_NAME_FOR_TESTING, status="failed", message="boom"
        )

        states.mark_pending(template)

        state = E2BSandboxTemplateSyncState.objects.get(template=template, cluster_name=CLUSTER_NAME_FOR_TESTING)
        assert (state.status, state.message) == (E2BTemplateSyncStatus.PENDING.value, "")


class TestResetUnsyncedToPending:
    def test_resets_states_not_current(self, clusters):
        """已成功下发当前配置的不动，同步期间要保持可用"""
        template = make_builtin_template("e2b-envd")
        changed = make_builtin_template("e2b-changed")
        clusters.broken_clusters.add(OTHER_CLUSTER)
        sync.sync_templates()
        # 下发成功之后配置又变了，例如摘要算法调整后上线
        type(changed).objects.filter(pk=changed.pk).update(image="new:v2")

        states.reset_unsynced_to_pending()

        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert set(status_of(changed).values()) == {E2BTemplateSyncStatus.PENDING.value}
        assert set(
            E2BSandboxTemplateSyncState.objects.filter(template=template).values_list("message", flat=True)
        ) == {""}

    def test_only_resets_states_in_scope(self, clusters):
        template = make_builtin_template("e2b-envd")
        other = make_builtin_template("e2b-other")
        sync.sync_templates()
        E2BSandboxTemplateSyncState.objects.update(status=E2BTemplateSyncStatus.FAILED.value)

        states.reset_unsynced_to_pending(cluster_names={OTHER_CLUSTER}, resource_names={"e2b-envd"})

        assert status_of(template) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.FAILED.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert set(status_of(other).values()) == {E2BTemplateSyncStatus.FAILED.value}


class TestDeleteClusterSyncStates:
    def test_drops_states_of_the_cluster_only(self, clusters):
        template = make_builtin_template("e2b-envd")
        sync.sync_templates()

        states.delete_cluster_sync_states(OTHER_CLUSTER)

        assert status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}
