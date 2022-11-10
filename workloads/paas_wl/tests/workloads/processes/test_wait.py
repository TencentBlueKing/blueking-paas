# -*- coding: utf-8 -*-
import copy
import datetime
import time
import uuid
from contextlib import contextmanager
from typing import List, Optional
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import PollingMetadata, PollingStatus
from django.dispatch import receiver

from paas_wl.release_controller.process.wait import (
    AbortedDetails,
    AbortedDetailsPolicy,
    DynamicReadyTimeoutPolicy,
    TooManyRestartsPolicy,
    UserInterruptedPolicy,
    WaitForAllStopped,
    WaitForReleaseAllReady,
    processes_updated,
)
from paas_wl.workloads.processes.models import Process

pytestmark = pytest.mark.django_db


@pytest.fixture
def metadata():
    return PollingMetadata(retries=0, query_started_at=time.time(), queried_count=0)


@pytest.fixture
def poller_mocker():
    @contextmanager
    def core(poller, processes: List[Process], last_processes: Optional[List[Process]] = None):
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
    def test_still_running(self, app, process, metadata, poller_mocker):
        poller = WaitForAllStopped(params={'engine_app_id': app.pk}, metadata=metadata)
        with poller_mocker(poller, [process]):
            status = poller.query()

        assert status.status == PollingStatus.DOING

    def test_all_stopped(self, app, process, metadata, poller_mocker):
        # Stop all processes
        process.instances = []
        poller = WaitForAllStopped(params={'engine_app_id': app.pk}, metadata=metadata)
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
    def test_broadcast(self, enabled, events_is_empty, app, process, metadata, poller_mocker):
        received_events = []

        @receiver(processes_updated)
        def _on_updated(sender, events, extra_params, **kwargs):
            for event in events:
                received_events.extend(events)

        last_process = copy.deepcopy(process)
        last_process.replicas = process.replicas + 1

        # Mark current query as the second try
        metadata.queried_count = 1
        poller = WaitForAllStopped(params={'engine_app_id': app.pk, 'broadcast_enabled': enabled}, metadata=metadata)
        with poller_mocker(poller, [process], [last_process]):
            _ = poller.query()

        if events_is_empty:
            assert len(received_events) == 0
        else:
            assert len(received_events) > 0


class TestWaitForReleaseAllReady:
    def test_not_ready(self, app, metadata, process, poller_mocker):
        processes = [process]
        poller = WaitForReleaseAllReady(params={'engine_app_id': app.pk, 'release_version': '10'}, metadata=metadata)
        with poller_mocker(poller, processes):
            status = poller.query()
        assert status.status == PollingStatus.DOING

    def test_ready(self, app, metadata, process, instance, poller_mocker):
        processes = [process]
        process.version = 10
        instance.version = 10
        instance.ready = True
        poller = WaitForReleaseAllReady(params={'engine_app_id': app.pk, 'release_version': '10'}, metadata=metadata)
        with poller_mocker(poller, processes):
            status = poller.query()
        assert status.status == PollingStatus.DONE

    def test_aborted_by_dynamic_timeout(self, app, process, poller_mocker):
        processes = [process]
        metadata = PollingMetadata(retries=0, query_started_at=0, queried_count=0)
        poller = WaitForReleaseAllReady(params={'engine_app_id': app.pk, 'release_version': '10'}, metadata=metadata)
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
    @pytest.fixture
    def fake_deployment(self):
        deployment = mock.MagicMock(pk=uuid.uuid4().hex)

        def retrieve_deployment(deployment_id):
            if deployment_id != deployment.pk:
                raise Exception
            return deployment

        with mock.patch("paas_wl.release_controller.process.wait.get_plat_client") as mocked:
            mocked().retrieve_deployment.side_effect = retrieve_deployment
            yield deployment

    def test_no_deployment_id(self, fake_deployment):
        ret = UserInterruptedPolicy().evaluate([], 0, extra_params={})
        assert ret is False

    def test_wrong_deployment_id(self, fake_deployment):
        ret = UserInterruptedPolicy().evaluate([], 0, extra_params={'deployment_id': uuid.uuid4().hex})
        assert ret is False

    def test_int_requested(self, fake_deployment):
        fake_deployment.release_int_requested_at = datetime.datetime.now()
        ret = UserInterruptedPolicy().evaluate([], 0, extra_params={'deployment_id': fake_deployment.pk})
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
