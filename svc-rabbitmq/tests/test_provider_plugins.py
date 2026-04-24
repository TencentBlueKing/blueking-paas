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

import pytest
from django.test import override_settings
from vendor.provider import DeadLetterRoutingProviderPlugin, HAProviderPlugin

from .conftest import make_cluster


@pytest.fixture()
def cluster():
    """Cluster with version 3.9.0 (>= 3.8, supports quorum)."""
    return make_cluster("3.9.0")


@pytest.fixture()
def old_cluster():
    """Cluster with version 3.7.0 (< 3.8, classic mirror only)."""
    return make_cluster("3.7.0")


class TestHAProviderPlugin:
    """HAProviderPlugin: version-based branching between quorum and classic mirror."""

    def test_quorum_path_for_version_gte_3_8(self, cluster, mock_client):
        """For RabbitMQ >= 3.8, HAProviderPlugin should use quorum queues."""
        plugin = HAProviderPlugin(context={}, client=mock_client, cluster=cluster, virtual_host="vh")
        plugin.on_create()

        mock_client.virtual_host.create.assert_called_once_with("vh", default_queue_type="quorum")
        mock_client.user_policy.create.assert_not_called()

    def test_classic_mirror_path_for_version_lt_3_8(self, old_cluster, mock_client):
        """For RabbitMQ < 3.8, HAProviderPlugin should use classic mirrored queues."""
        plugin = HAProviderPlugin(context={}, client=mock_client, cluster=old_cluster, virtual_host="vh")
        plugin.on_create()

        mock_client.virtual_host.create.assert_not_called()
        mock_client.user_policy.create.assert_called_once()
        _, args, _ = mock_client.user_policy.create.mock_calls[0]
        assert args[0] == "vh"
        assert args[1] == HAProviderPlugin.HA_POLICY_NAME
        assert args[2]["definition"]["ha-mode"] == "all"

    @override_settings(RABBITMQ_HA_POLICY_ENABLED=False)
    def test_noop_when_disabled(self, cluster, mock_client):
        """Setting disabled → no calls at all."""
        plugin = HAProviderPlugin(context={}, client=mock_client, cluster=cluster, virtual_host="vh")
        plugin.on_create()

        mock_client.virtual_host.create.assert_not_called()
        mock_client.user_policy.create.assert_not_called()


class TestDeadLetterRoutingProviderPlugin:
    """DeadLetterRoutingProviderPlugin: dead letter exchange/queue setup with quorum awareness."""

    DLX_SETTINGS = {
        "RABBITMQ_DEFAULT_DEAD_LETTER_ROUTING_KEY": "",
        "RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE": "dlx.exchange",
        "RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_TYPE": "direct",
        "RABBITMQ_DEFAULT_DEAD_LETTER_EXCHANGE_DURABLE": False,
        "RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE": "dlx.queue",
        "RABBITMQ_DEFAULT_DEAD_LETTER_QUEUE_DURABLE": False,
    }

    @override_settings(**DLX_SETTINGS)
    def test_quorum_queue_for_version_gte_3_8(self, cluster, mock_client):
        """DLQ declared as quorum type with durable=True for >= 3.8."""
        ctx = {}
        plugin = DeadLetterRoutingProviderPlugin(context=ctx, client=mock_client, cluster=cluster, virtual_host="vh")
        plugin.on_create()

        _, kwargs = mock_client.queue.declare.call_args
        assert kwargs["arguments"] == {"x-queue-type": "quorum"}
        assert kwargs["durable"] is True

    override_settings(**DLX_SETTINGS)

    def test_classic_queue_for_version_lt_3_8(self, old_cluster, mock_client):
        """DLQ declared without quorum arguments for < 3.8."""
        plugin = DeadLetterRoutingProviderPlugin(
            context={}, client=mock_client, cluster=old_cluster, virtual_host="vh"
        )
        plugin.on_create()

        _, kwargs = mock_client.queue.declare.call_args
        assert kwargs["arguments"] == {}
        assert kwargs["durable"] is False

    @override_settings(**DLX_SETTINGS)
    def test_skipped_for_version_lt_2_8(self, mock_client):
        """Versions below 2.8 → on_create is a no-op."""
        c = make_cluster("2.7.0")
        plugin = DeadLetterRoutingProviderPlugin(context={}, client=mock_client, cluster=c, virtual_host="vh")
        plugin.on_create()

        mock_client.exchange.declare.assert_not_called()
        mock_client.queue.declare.assert_not_called()

    @override_settings(**DLX_SETTINGS)
    def test_context_populated(self, cluster, mock_client):
        """After on_create, context should contain dlx-* keys."""
        ctx = {}
        plugin = DeadLetterRoutingProviderPlugin(context=ctx, client=mock_client, cluster=cluster, virtual_host="vh")
        plugin.on_create()

        assert ctx["dlx-exchange"] == "dlx.exchange"
        assert ctx["dlx-queue"] == "dlx.queue"
        assert ctx["dlx-routing-key"] == ""
