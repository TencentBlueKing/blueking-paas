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
import io
import time
from textwrap import dedent
from unittest import mock

import pytest
from blue_krill.contextlib import nullcontext as does_not_raise

from paasng.engine.constants import DeployEventStatus, JobStatus
from paasng.engine.deploy.exceptions import DeployShouldAbortError
from paasng.engine.deploy.infras import (
    ConsoleStream,
    DeploymentCoordinator,
    DeployProcedure,
    InternalEvent,
    InternalEventParser,
    MessageStepMatcher,
    ServerSendEvent,
    get_env_variables,
)
from paasng.engine.exceptions import InternalEventFormatError
from paasng.engine.models import DeployPhase, DeployPhaseTypes
from paasng.engine.models.config_var import ConfigVar
from paasng.engine.models.managers import DeployPhaseManager
from paasng.engine.models.steps import DeployStep, DeployStepMeta
from paasng.extensions.declarative.exceptions import DescriptionValidationError
from paasng.extensions.declarative.handlers import AppDescriptionHandler
from tests.utils.helpers import BaseTestCaseWithApp
from tests.utils.mocks.engine import replace_cluster_service

from .setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_cluster():
    with replace_cluster_service():
        yield


@pytest.fixture(autouse=True)
def setup_mocks(mock_current_engine_client):
    """Setup mocks for current testing module

    - Mock engine client
    """
    yield


class TestDeployProcedure:
    @pytest.fixture
    def phases(self, bk_prod_env, bk_deployment):
        manager = DeployPhaseManager(bk_prod_env)
        phases = manager.get_or_create_all()
        for p in phases:
            manager.attach(DeployPhaseTypes(p.type), bk_deployment)
        return phases

    def test_normal(self, phases):
        stream = ConsoleStream()
        stream.write_title = mock.Mock()  # type: ignore

        with DeployProcedure(stream, None, 'doing nothing', phases[0]):
            pass

        assert stream.write_title.call_count == 1
        assert stream.write_title.call_args == ((DeployProcedure.TITLE_PREFIX + 'doing nothing',),)

    def test_with_expected_error(self, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        try:
            with DeployProcedure(stream, None, 'doing nothing', phases[0]):
                raise DeployShouldAbortError('oops')
        except DeployShouldAbortError:
            pass

        assert stream.write_message.call_count == 1
        assert stream.write_message.call_args[0][0].endswith('oops。')

    def test_with_unexpected_error(self, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        try:
            with DeployProcedure(stream, None, 'doing nothing', phases[0]):
                raise ValueError('oops')
        except ValueError:
            pass

        assert stream.write_message.call_count == 1
        # The error message should not contains the original exception message
        assert 'oops' not in stream.write_message.call_args[0][0]

    def test_with_deployment(self, bk_deployment, phases):
        stream = ConsoleStream()
        stream.write_message = mock.Mock()  # type: ignore

        # 手动标记该阶段的开启, 但 title 未知
        with DeployProcedure(stream, bk_deployment, 'doing nothing', phases[0]) as d:
            assert not d.step_obj

        # title 已知，但是阶段不匹配
        with DeployProcedure(stream, bk_deployment, '检测部署结果', phases[0]) as d:
            assert not d.step_obj

        # 正常
        with DeployProcedure(stream, bk_deployment, '配置资源实例', phases[0]) as d:
            assert d.step_obj


class TestGetEnvVariables:
    def test_user_config_var(self, bk_module, bk_stag_env):
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='FOO', value='bar')
        env_vars = get_env_variables(bk_stag_env)
        assert env_vars['FOO'] == 'bar'

    def test_builtin_id_and_secret(self, bk_app, bk_stag_env):
        env_vars = get_env_variables(bk_stag_env)
        assert env_vars['BKPAAS_APP_ID'] == bk_app.code
        assert env_vars['BKPAAS_APP_SECRET'] != ''

    @pytest.mark.parametrize(
        "yaml_content, ctx",
        [
            (
                dedent(
                    '''
                    version: 1
                    module:
                        env_variables:
                            - key: FOO_DESC
                              value: bar
                        language: python
                    '''
                ),
                does_not_raise({"FOO_DESC": "bar"}),
            ),
            (
                dedent(
                    '''
                    version: 1
                    module:
                        env_variables:
                            - key: FOO
                              value: will be overwrite
                        language: python
                    '''
                ),
                does_not_raise({"FOO": "bar"}),
            ),
            (
                dedent(
                    '''
                    version: 1
                    module:
                        env_variables:
                            - key: FOO_DESC
                              value: bar
                            - key: BKPAAS_RESERVED_KEY
                              value: raise error
                        language: python
                    '''
                ),
                pytest.raises(DescriptionValidationError),
            ),
        ],
    )
    def test_part_declarative(self, bk_module, bk_stag_env, bk_app, bk_deployment, yaml_content, ctx):
        fp = io.StringIO(yaml_content)
        ConfigVar.objects.create(module=bk_module, environment=bk_stag_env, key='FOO', value='bar')
        with ctx as expected:
            AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
            env_vars = get_env_variables(bk_stag_env, deployment=bk_deployment)
            for key, value in expected.items():
                assert key in env_vars
                assert env_vars[key] == value

    def test_part_saas_services(self, bk_stag_env, bk_deployment):
        yaml_content = dedent(
            '''
            version: 1
            module:
                svc_discovery:
                    bk_saas:
                        - bk_app_code: foo-app
                        - bk_app_code: bar-app
                          module_name: api
                language: python
            '''
        )
        fp = io.StringIO(yaml_content)
        AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
        env_vars = get_env_variables(bk_stag_env, deployment=bk_deployment)
        assert 'BKPAAS_SERVICE_ADDRESSES_BKSAAS' in env_vars


class TestDeploymentCoordinator(BaseTestCaseWithApp):
    def setUp(self):
        super().setUp()
        self.env = self.module.envs.get(environment='stag')
        self.deployment = create_fake_deployment(self.module)

    def test_normal(self):
        env_mgr = DeploymentCoordinator(self.env)
        assert env_mgr.acquire_lock() is True
        assert env_mgr.acquire_lock() is False
        env_mgr.release_lock()

        # Re-initialize a new object
        env_mgr = DeploymentCoordinator(self.env)
        assert env_mgr.acquire_lock() is True
        env_mgr.release_lock()

    def test_lock_timeout(self):
        env_mgr = DeploymentCoordinator(self.env, timeout=0.1)
        assert env_mgr.acquire_lock() is True
        assert env_mgr.acquire_lock() is False

        # wait for lock timeout
        time.sleep(0.2)
        assert env_mgr.acquire_lock() is True
        env_mgr.release_lock()

    def test_release_without_deployment(self):
        env_mgr = DeploymentCoordinator(self.env)
        env_mgr.acquire_lock()
        env_mgr.set_deployment(self.deployment)

        # Get ongoing deployment
        env_mgr = DeploymentCoordinator(self.env)
        assert env_mgr.get_current_deployment() == self.deployment
        env_mgr.release_lock()
        assert env_mgr.get_current_deployment() is None

    def test_release_with_deployment(self):
        env_mgr = DeploymentCoordinator(self.env)
        env_mgr.acquire_lock()
        env_mgr.set_deployment(self.deployment)

        env_mgr = DeploymentCoordinator(self.env)
        env_mgr.release_lock(self.deployment)
        assert env_mgr.get_current_deployment() is None

    def test_release_with_wrong_deployment(self):
        env_mgr = DeploymentCoordinator(self.env)
        env_mgr.acquire_lock()
        env_mgr.set_deployment(self.deployment)

        deployment = create_fake_deployment(self.module)
        env_mgr = DeploymentCoordinator(self.env)
        with pytest.raises(ValueError):
            env_mgr.release_lock(deployment)

        assert env_mgr.get_current_deployment() == self.deployment


class TestServerSendEvent:
    @pytest.mark.parametrize("eid, event, data_dict", [("1", "xxxx", {"aaa": "bbb"}), (333, "xxxx", {})])
    def test_from_raw_normal(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))

        assert e.id == eid
        assert e.event == event
        assert e.data == data_dict
        assert not e.is_internal

    @pytest.mark.parametrize("eid, event, data_dict", [("1", "message", {"aaa": "bbb"}), ("1", "msg", {"aaa": "bbb"})])
    def test_from_raw_message(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))

        assert e.id == eid
        assert e.event == "message"
        assert e.data == data_dict
        assert not e.is_internal

    @pytest.mark.parametrize(
        "eid, event, data_dict", [("1", "internal", {"aaa": "bbb"}), ("1", "internal", {"aaa": "bbb"})]
    )
    def test_from_raw_internal(self, eid, event, data_dict):
        """测试正常加载 raw event"""
        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        assert e.is_internal

    @pytest.mark.parametrize("eid, event, data_dict", [("1", "internal", {"aaa": "bbb"})])
    def test_to_yield_str_list(self, eid, event, data_dict):
        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        assert e.to_yield_str_list() == ['id: %s\n' % e.id, 'event: %s\n' % e.event, 'data: %s\n\n' % e.data]


class TestInternalEvent:
    """测试内部事件"""

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "internal", {"name": "111", "type": "aaa", "status": "started"}),
            ("1", "internal", {"name": "222", "type": "bbb", "status": "finished"}),
            ("1", "internal", {"name": "333", "type": "ccc", "status": "aborted"}),
        ],
    )
    def test_from_general_event(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        i = InternalEvent.from_general_event(e)

        assert i.is_internal
        assert i.publisher == "unknown"
        assert i.name == data_dict["name"]
        assert i.type == data_dict["type"]
        assert i.status.value == data_dict["status"]

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "xxx", {"name": "111", "type": "aaa", "status": "started"}),
            ("1", "interal", {"name": "222", "type": "bbb", "status": "finished"}),
            ("1", "inter", {"name": "333", "type": "ccc", "status": "aborted"}),
        ],
    )
    def test_no_internal(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        with pytest.raises(InternalEventFormatError):
            InternalEvent.from_general_event(e)

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "internal", {"name": "111", "type": "aaa"}),
            ("1", "internal", {"name": "222", "status": "finished"}),
            ("1", "internal", {"type": "ccc", "status": "aborted"}),
        ],
    )
    def test_no_required_data_field(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        with pytest.raises(InternalEventFormatError):
            InternalEvent.from_general_event(e)

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "internal", {"name": "111", "type": "aaa", "status": "started", "publisher": "engine"}),
            ("1", "internal", {"name": "111", "type": "aaa", "status": "started", "publisher": "xxxxxx"}),
            ("1", "internal", {"name": "111", "type": "aaa", "status": "started", "publisher": "unknown"}),
        ],
    )
    def test_publisher(self, eid, event, data_dict):
        """测试正常加载 raw event"""

        e = ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict))
        i = InternalEvent.from_general_event(e)
        assert i.publisher == data_dict["publisher"]

    @pytest.fixture
    def build_phase(self, bk_stag_env) -> DeployPhase:
        return DeployPhaseManager(bk_stag_env)._get_or_create(DeployPhaseTypes.BUILD)

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "internal", {"name": "检测进程类型", "type": "step", "status": "started", "publisher": "engine"}),
            ("1", "internal", {"name": "检测进程类型", "type": "step", "status": "finished", "publisher": "engine"}),
            ("1", "internal", {"name": "检测进程类型", "type": "step", "status": "aborted", "publisher": "engine"}),
        ],
    )
    def test_invoke(self, build_phase, eid, event, data_dict):
        step_obj = build_phase.get_step_by_name(data_dict["name"])
        i = InternalEvent.from_general_event(ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict)))
        i.invoke(step_obj, ConsoleStream())

        assert step_obj.status == DeployEventStatus.get_job_status(DeployEventStatus(data_dict["status"])).value

    @pytest.mark.parametrize(
        "eid, event, data_dict, job_status",
        [
            (
                "1",
                "internal",
                {"name": "检测进程类型", "type": "step", "status": "finished", "publisher": "engine"},
                JobStatus.SUCCESSFUL,
            ),
            (
                "1",
                "internal",
                {"name": "检测进程类型", "type": "step", "status": "aborted", "publisher": "engine"},
                JobStatus.FAILED,
            ),
            (
                "1",
                "internal",
                {"name": "检测进程类型", "type": "step", "status": "started", "publisher": "engine"},
                JobStatus.PENDING,
            ),
        ],
    )
    def test_same_status_invoke(self, build_phase, eid, event, data_dict, job_status):
        # 不更新 start_time 或者 complete_time 字段，方便后续判断是否执行
        step_obj = build_phase.get_step_by_name(data_dict["name"])
        step_obj.status = job_status.value
        step_obj.save()

        i = InternalEvent.from_general_event(ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict)))
        i.invoke(step_obj, ConsoleStream())

        assert not step_obj.start_time
        assert step_obj.status == DeployEventStatus.get_job_status(DeployEventStatus(data_dict["status"])).value
        assert not step_obj.start_time

    @pytest.mark.parametrize(
        "eid, event, data_dict, job_status",
        [
            (
                "1",
                "internal",
                {"name": "检测进程类型", "type": "step", "status": "started", "publisher": "engine"},
                JobStatus.SUCCESSFUL,
            ),
            (
                "1",
                "internal",
                {"name": "检测进程类型", "type": "step", "status": "started", "publisher": "engine"},
                JobStatus.FAILED,
            ),
        ],
    )
    def test_finished_status_invoke(self, build_phase, eid, event, data_dict, job_status):
        # 不更新 start_time 或者 complete_time 字段，方便后续判断是否执行
        step_obj = build_phase.get_step_by_name(data_dict["name"])
        step_obj.status = job_status.value
        step_obj.save()

        i = InternalEvent.from_general_event(ServerSendEvent.from_raw(dict(id=eid, event=event, data=data_dict)))
        i.invoke(step_obj, ConsoleStream())

        assert not step_obj.start_time
        assert step_obj.status == job_status.value
        assert not step_obj.start_time


class TestInternalEventParser:
    """测试内部时间解析器"""

    def parser(self, target_type: str, target_publisher: str) -> InternalEventParser:
        return InternalEventParser(target_event_type=target_type, target_publisher=target_publisher)

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "internal", {"name": "111", "type": "aaa", "status": "started", "publisher": "engine"}),
        ],
    )
    def test_normal_parse(self, eid, event, data_dict):
        e = self.parser("aaa", "engine").parse_event(dict(id=eid, event=event, data=data_dict))
        assert e
        assert e.event == event
        assert e.publisher == data_dict["publisher"]

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "internal", {"name": "111", "type": "aaa", "status": "started", "publisher": "engine"}),
        ],
    )
    def test_wrong_type(self, eid, event, data_dict):
        e = self.parser("bbb", "engine").parse_event(dict(id=eid, event=event, data=data_dict))
        assert e is None

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "internal", {"name": "111", "type": "aaa", "status": "started", "publisher": "engine"}),
        ],
    )
    def test_wrong_publisher(self, eid, event, data_dict):
        e = self.parser("aaa", "xxxx").parse_event(dict(id=eid, event=event, data=data_dict))
        assert e is None

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        [
            ("1", "xxxx", {"name": "111", "type": "aaa", "status": "started", "publisher": "engine"}),
        ],
    )
    def test_no_internal(self, eid, event, data_dict):
        e = self.parser("aaa", "engine").parse_event(dict(id=eid, event=event, data=data_dict))
        assert e is None

    @pytest.mark.parametrize(
        "eid, event, data_dict",
        # no internal
        [
            ("1", "xxxx", {"name": "111", "type": "aaa", "status": "started", "publisher": "engine"}),
            # wrong data
            ("1", "xxxx", {"type": "aaa", "status": "started", "publisher": "engine"}),
            # wrong data
            ("1", "internal", {"type": "aaa", "status": "started"}),
            # empty event
            ("1", "", {}),
        ],
    )
    def test_wrong_format(self, eid, event, data_dict):
        e = self.parser("aaa", "engine").parse_event(dict(id=eid, event=event, data=data_dict))
        assert e is None


class TestMessageStepMatcher:
    """测试 message 步骤匹配器"""

    @pytest.fixture
    def make_phase_and_steps(self, bk_deployment):
        def _make(phase_type: DeployPhaseTypes, pattern_maps: dict):
            phase = DeployPhase.objects.create(
                type=phase_type.value, engine_app=bk_deployment.get_engine_app(), deployment=bk_deployment
            )

            for step_name, patterns in pattern_maps.items():
                meta = DeployStepMeta.objects.create(
                    phase=phase_type.value,
                    name=step_name,
                    started_patterns=patterns[0],
                    finished_patterns=patterns[1],
                )

                DeployStep.objects.create(name=step_name, phase=phase, meta=meta)

            return phase

        return _make

    @staticmethod
    def make_events_by_lines(lines):
        events = []
        for index, x in enumerate(lines):
            events.append(ServerSendEvent(id=str(index), event="message", data={"line": x}))
        return events

    @pytest.mark.parametrize(
        "lines,pattern_maps,expected",
        [
            (
                ["xxxx", "yyyy", "qqq"],
                {
                    "aa": (["xxx"], ["yyy"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": "successful", "bb": "pending"},
            ),
            (
                ["xxxx", "yyyy"],
                {
                    "aa": (["xxx"], ["yyy"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": "successful", "bb": None},
            ),
            (
                ["xxxx", "www"],
                {
                    "aa": (["xxx"], ["yyy"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": "pending", "bb": "successful"},
            ),
            (
                ["asdfasdf", "uiuiui"],
                {
                    "aa": (["xxx"], ["yyy"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": None, "bb": None},
            ),
            (
                ["-- asdfasdf -- ", "xxx xxx"],
                {
                    "aa": (["-- .+ --"], ["xxx .+"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": "successful", "bb": None},
            ),
            (
                [
                    "\u001b[0m\u001b[1m-----> Step setup begin\n",
                    "\u001b[0m\u001b[3m * Step setup done, duration 4.350117102s\n",
                ],
                {
                    "aa": ([".+-----> Step detect begin"], [".+Step setup done.+"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": "successful", "bb": None},
            ),
            (
                [
                    "\u001b[0m\u001b[m-----> Creating runtime environment\n",
                    "\u001b[0m\u001b[m-----> Installing binaries\n",
                ],
                {
                    "aa": ([".+Creating runtime environment"], [".+Installing binaries"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": "successful", "bb": None},
            ),
            (
                [
                    "\u001b[0m\u001b[1m-----> Step build begin\n",
                    "\u001b[0m\u001b[1m-----> Build success\n",
                ],
                {
                    "aa": ([".+Step build begin"], [".+-----> Build success"]),
                    "bb": (["qqq"], ["www"]),
                },
                {"aa": "successful", "bb": None},
            ),
        ],
    )
    def test_match_and_update(self, lines, pattern_maps, make_phase_and_steps, expected):
        """"""
        phase = make_phase_and_steps(DeployPhaseTypes.BUILD, pattern_maps)
        saved_maps = {
            JobStatus.PENDING: phase.get_started_pattern_map(),
            JobStatus.SUCCESSFUL: phase.get_finished_pattern_map(),
        }

        for e in self.make_events_by_lines(lines):
            MessageStepMatcher.match_and_update_step(e, saved_maps, phase)

        steps_status = {}
        for x in phase.steps.all().values("name", "status"):
            steps_status[x["name"]] = x["status"]

        assert steps_status == expected
