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

from paasng.engine.constants import JobStatus
from paasng.engine.deploy.workflow.messaging import MessageStepMatcher, ServerSendEvent
from paasng.engine.models import DeployPhase, DeployPhaseTypes
from paasng.engine.models.steps import DeployStep, DeployStepMeta

pytestmark = pytest.mark.django_db


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
