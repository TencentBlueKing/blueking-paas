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
from django.core.management import call_command
from django.core.management.base import CommandError
from vendor.models import Cluster

BASE_ARGS = ["--name", "ai-agent", "--host", "10.0.0.1", "--password", "secret", "--cluster-version", "3.9.0"]


def tags_of(cluster: Cluster) -> dict:
    return {tag.key: tag.value for tag in cluster.tags.all()}


@pytest.mark.django_db
class TestRegisterCluster:
    def test_create_with_tags(self):
        call_command("register_cluster", *BASE_ARGS, "--tag", "usage=ai_agent", "--extra", '{"tls": {"ca": "x"}}')

        cluster = Cluster.objects.get(name="ai-agent")
        assert cluster.management_api == "http://10.0.0.1:15672"
        assert cluster.enable is True
        assert cluster.extra == {"tls": {"ca": "x"}}
        assert tags_of(cluster) == {"usage": "ai_agent"}

    def test_update_replaces_tags(self):
        call_command("register_cluster", *BASE_ARGS, "--tag", "usage=ai_agent", "--tag", "region=sz")
        call_command("register_cluster", *BASE_ARGS, "--tag", "usage=other", "--disable")

        cluster = Cluster.objects.get(name="ai-agent")
        assert cluster.enable is False
        assert tags_of(cluster) == {"usage": "other"}

    def test_dry_run(self):
        call_command("register_cluster", *BASE_ARGS, "--tag", "usage=ai_agent", "--dry-run")

        assert not Cluster.objects.exists()

    @pytest.mark.parametrize("tag", ["usage", "=ai_agent", "usage="])
    def test_invalid_tag(self, tag):
        with pytest.raises(CommandError, match="expected key=value"):
            call_command("register_cluster", *BASE_ARGS, "--tag", tag)
