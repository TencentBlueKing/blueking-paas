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
from paasng.platform.agent_sandbox.e2b.template_sync import records, sync
from paasng.platform.agent_sandbox.models import E2BSandboxTemplateSyncRecord
from tests.paasng.platform.agent_sandbox.e2b.helpers import make_builtin_template, make_custom_template
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

from .fakes import OTHER_CLUSTER, status_of

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestMarkPending:
    def test_marks_target_clusters_pending(self, bk_app):
        builtin = make_builtin_template("e2b-envd")
        custom = make_custom_template(bk_app, "mine")

        records.mark_pending(builtin)
        records.mark_pending(custom)

        assert status_of(builtin) == {
            CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value,
            OTHER_CLUSTER: E2BTemplateSyncStatus.PENDING.value,
        }
        assert status_of(custom) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.PENDING.value}

    def test_overwrites_previous_result(self):
        template = make_builtin_template("e2b-envd")
        E2BSandboxTemplateSyncRecord.objects.create(
            template=template, cluster_name=CLUSTER_NAME_FOR_TESTING, status="failed", message="boom"
        )

        records.mark_pending(template)

        record = E2BSandboxTemplateSyncRecord.objects.get(template=template, cluster_name=CLUSTER_NAME_FOR_TESTING)
        assert (record.status, record.message) == (E2BTemplateSyncStatus.PENDING.value, "")


class TestDeleteClusterRecords:
    def test_drops_records_of_the_cluster_only(self, clusters):
        template = make_builtin_template("e2b-envd")
        sync.sync_templates()

        records.delete_cluster_records(OTHER_CLUSTER)

        assert status_of(template) == {CLUSTER_NAME_FOR_TESTING: E2BTemplateSyncStatus.SUCCEEDED.value}
