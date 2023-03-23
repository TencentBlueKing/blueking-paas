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
import copy
import datetime
import time
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, List, Optional
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import PollingMetadata, PollingStatus
from django.dispatch import receiver

from paasng.engine.processes.wait import (
    AbortedDetails,
    AbortedDetailsPolicy,
    DynamicReadyTimeoutPolicy,
    TooManyRestartsPolicy,
    UserInterruptedPolicy,
    WaitForAllStopped,
    WaitForReleaseAllReady,
    processes_updated,
)

if TYPE_CHECKING:
    from paas_wl.workloads.processes.models import Process

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.fixture
def metadata():
    return PollingMetadata(retries=0, query_started_at=time.time(), queried_count=0)


@pytest.fixture
def poller_mocker():
    @contextmanager
    def core(poller, processes: 'List[Process]', last_processes: 'Optional[List[Process]]' = None):
        with mock.patch.object(poller, "_get_last_processes") as last, mock.patch.object(
            poller, "_get_current_processes"
        ) as current:
            current.return_value = processes
            last.return_value = processes if not last_processes else last_processes
            yield

    return core


class TestDynamicReadyTimeoutPolicy:
    @pytest.mark.parametrize(
        'desired_replicas,already_waited,desired_result',
        [
            # small replicas
            (1, 60 * 3 - 1, False),
            (1, 60 * 3 + 1, True),
            # replicas greater than max value
            (100, 60 * 15 - 1, False),
            (100, 60 * 15 + 1, True),
        ],
    )
    def test_evaluate(self, desired_replicas, already_waited, desired_result, process):
        process.replicas = desired_replicas
        assert (
            DynamicReadyTimeoutPolicy().evaluate([process], already_waited=already_waited, extra_params={})
            is desired_result
        )


class TestWaitForAllStopped:
    def test_still_running(self, bk_stag_env, process, metadata, poller_mocker):
        poller = WaitForAllStopped(params={'env_id': bk_stag_env.id}, metadata=metadata)
        with poller_mocker(poller, [process]):
            status = poller.query()

        assert status.status == PollingStatus.DOING

    def test_all_stopped(self, bk_stag_env, process, metadata, poller_mocker):
        # Stop all processes
        process.instances = []
        poller = WaitForAllStopped(params={'env_id': bk_stag_env.id}, metadata=metadata)
        with poller_mocker(poller, [process]):
            status = poller.query()
        assert status.status == PollingStatus.DONE

    @pytest.mark.parametrize(
        'enabled, events_is_empty',
        [
            (True, False),
            (False, True),
        ],
    )
    def test_broadcast(self, enabled, events_is_empty, bk_stag_env, process, metadata, poller_mocker):
        received_events = []

        @receiver(processes_updated)
        def _on_updated(sender, events, extra_params, **kwargs):
            received_events.extend(events)

        last_process = copy.deepcopy(process)
        last_process.replicas = process.replicas + 1

        # Mark current query as the second try
        metadata.queried_count = 1
        poller = WaitForAllStopped(params={'env_id': bk_stag_env.id, 'broadcast_enabled': enabled}, metadata=metadata)
        with poller_mocker(poller, [process], [last_process]):
            _ = poller.query()

        if events_is_empty:
            assert len(received_events) == 0
        else:
            assert len(received_events) > 0


class TestWaitForReleaseAllReady:
    def test_not_ready(self, bk_stag_env, metadata, process, poller_mocker):
        processes = [process]
        poller = WaitForReleaseAllReady(params={'env_id': bk_stag_env.id, 'release_version': '10'}, metadata=metadata)
        with poller_mocker(poller, processes):
            status = poller.query()
        assert status.status == PollingStatus.DOING

    def test_ready(self, bk_stag_env, metadata, process, instance, poller_mocker):
        processes = [process]
        process.version = 10
        instance.version = 10
        instance.ready = True
        poller = WaitForReleaseAllReady(params={'env_id': bk_stag_env.id, 'release_version': '10'}, metadata=metadata)
        with poller_mocker(poller, processes):
            status = poller.query()
        assert status.status == PollingStatus.DONE

    def test_aborted_by_dynamic_timeout(self, bk_stag_env, process, poller_mocker):
        processes = [process]
        metadata = PollingMetadata(retries=0, query_started_at=0, queried_count=0)
        poller = WaitForReleaseAllReady(params={'env_id': bk_stag_env.id, 'release_version': '10'}, metadata=metadata)
        with poller_mocker(poller, processes):
            status = poller.query()
        assert status.status == PollingStatus.DONE
        assert status.data is not None
        assert status.data['aborted'] is True


class TestTooManyRestartsPolicy:
    @pytest.mark.parametrize(
        'restart_count, instance_has_different_version, desired_result',
        [
            (0, False, False),
            (3, False, False),
            (4, False, True),
            (4, True, False),
        ],
    )
    def test_evaluate(self, restart_count, instance_has_different_version, desired_result, process, instance):
        instance.version = (process.version + 1) if instance_has_different_version else process.version
        instance.restart_count = restart_count
        assert TooManyRestartsPolicy().evaluate([process], already_waited=0, extra_params={}) is desired_result


class TestUserInterruptedPolicy:
    def test_no_deployment_id(self):
        ret = UserInterruptedPolicy().evaluate([], 0, extra_params={})
        assert ret is False

    def test_wrong_deployment_id(self):
        ret = UserInterruptedPolicy().evaluate([], 0, extra_params={'deployment_id': uuid.uuid4().hex})
        assert ret is False

    def test_int_requested(self, bk_deployment):
        bk_deployment.release_int_requested_at = datetime.datetime.now()
        bk_deployment.save()
        ret = UserInterruptedPolicy().evaluate([], 0, extra_params={'deployment_id': bk_deployment.pk})
        assert ret is True


class TestAbortedDetails:
    def test_truth_value(self):
        v = AbortedDetails(aborted=True, policy=AbortedDetailsPolicy(reason='foo', name='bar'))
        assert v.dict() == {
            'aborted': True,
            'policy': {'reason': 'foo', 'name': 'bar', 'is_interrupted': False},
            'extra_data': None,
        }

    def test_falsehood_value(self):
        v = AbortedDetails(aborted=False, extra_data='foo')
        assert v.dict() == {'aborted': False, 'policy': None, 'extra_data': 'foo'}

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            _ = AbortedDetails(aborted=True)
