# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import Dict
from unittest import mock

import pytest

from paasng.dev_resources.servicehub.services import PlanObj, ServiceSpecificationHelper

from .utils import gen_plan, generate_ssd

pytestmark = pytest.mark.django_db


class TestServiceSpecificationHelper:
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_create_init(self, mock_get_plans, bk_plan_r1_v1, bk_service_r1):
        mock_get_plans.return_value = [bk_plan_r1_v1]
        helper_from_svc = ServiceSpecificationHelper.from_service(bk_service_r1)
        assert len(helper_from_svc.plans) == 1
        helper_from_init = ServiceSpecificationHelper(bk_service_r1.specifications, [bk_plan_r1_v1])
        assert helper_from_svc.plans == helper_from_init.plans

    @pytest.mark.parametrize(
        "action, ssd_list, spec_fields_cnt, values_cnt",
        [
            ("from_service", [generate_ssd(), generate_ssd("app_zone")], 2, 2),
            ("from_service", [generate_ssd(), generate_ssd(), generate_ssd("app_zone")], 3, 3),
            ("from_service", [generate_ssd(), generate_ssd(), generate_ssd(), generate_ssd("app_zone")], 4, 4),
            ("from_service_public_specifications", [generate_ssd(), generate_ssd("app_zone")], 1, 1),
            ("from_service_public_specifications", [generate_ssd(), generate_ssd(), generate_ssd("app_zone")], 2, 2),
            (
                "from_service_public_specifications",
                [generate_ssd(), generate_ssd(), generate_ssd(), generate_ssd("app_zone")],
                3,
                3,
            ),
            ("from_service_protected_specifications", [generate_ssd(), generate_ssd("app_zone")], 1, 1),
            (
                "from_service_protected_specifications",
                [generate_ssd(), generate_ssd(), generate_ssd("app_zone")],
                1,
                1,
            ),
            (
                "from_service_protected_specifications",
                [generate_ssd(), generate_ssd(), generate_ssd(), generate_ssd("app_zone")],
                1,
                1,
            ),
        ],
    )
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_create(self, mock_get_plans, bk_plan_r1_v1, bk_service_r1, action, ssd_list, spec_fields_cnt, values_cnt):
        mock_get_plans.return_value = [bk_plan_r1_v1]
        bk_service_r1.specifications = ssd_list

        helper = getattr(ServiceSpecificationHelper, action)(bk_service_r1)
        assert helper.plans == [bk_plan_r1_v1]

        plans_spec_value = helper.list_plans_spec_value()
        recommended_specs = helper.get_recommended_spec()

        assert len(plans_spec_value) == len([bk_plan_r1_v1])
        spec_value = plans_spec_value[0]

        assert len(spec_value) == spec_fields_cnt
        assert len(recommended_specs) == values_cnt
        if action in ["from_service_protected_specifications", "from_service"]:
            assert "app_zone" in recommended_specs

    @pytest.mark.parametrize(
        "action, ssd_list",
        [
            ("from_service", [generate_ssd(name="app_zone")] * 2 + [generate_ssd()] * 2),
            ("from_service_public_specifications", [generate_ssd()] * 2),
            ("from_service_protected_specifications", [generate_ssd(name="app_zone")] * 2),
        ],
    )
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_create_from_duplicated_specifications(
        self, mock_get_plans, bk_plan_r1_v1, bk_service_r1, action, ssd_list
    ):
        mock_get_plans.return_value = [bk_plan_r1_v1]
        bk_service_r1.specifications = ssd_list

        with pytest.raises(ValueError) as exec_info:
            getattr(ServiceSpecificationHelper, action)(bk_service_r1)
        assert "Encountered duplicate field name" in str(exec_info.value)

    @pytest.mark.parametrize(
        "filters, expected",
        [
            ({"version": "1"}, ["bk_plan_r1_v1", "bk_plan_r2_v1"]),
            ({"app_zone": "1"}, ["bk_plan_r1_v1", "bk_plan_r1_v2"]),
            ({"version": "2"}, ["bk_plan_r1_v2"]),
            ({"app_zone": "2"}, ["bk_plan_r2_v1"]),
        ],
    )
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_filter_plans(
        self, mock_get_plans, bk_plan_r1_v1, bk_plan_r1_v2, bk_plan_r2_v1, bk_service_r1, filters, expected
    ):
        mock_get_plans.return_value = [bk_plan_r1_v1, bk_plan_r1_v2, bk_plan_r2_v1]
        bk_service_r1.specifications = [generate_ssd("version"), generate_ssd("app_zone")]
        plan_maps: Dict[str, PlanObj] = {
            "bk_plan_r1_v1": bk_plan_r1_v1,
            "bk_plan_r1_v2": bk_plan_r1_v2,
            "bk_plan_r2_v1": bk_plan_r2_v1,
        }
        helper = ServiceSpecificationHelper.from_service(bk_service_r1)

        uuids = {plan.uuid for plan in helper.filter_plans(specifications=filters)}
        assert uuids == {plan_maps[attr].uuid for attr in expected}

    @pytest.mark.parametrize(
        "service_ssd_list, extra_plans, expected",
        [
            ([generate_ssd("app_zone")], [gen_plan("r1", specifications={})], {'1': None, '2': None, None: None}),
            ([generate_ssd("version")], [gen_plan("r1", specifications={})], {'1': None, '2': None, None: None}),
            (
                [generate_ssd("version"), generate_ssd("app_zone")],
                [gen_plan("r1", specifications={})],
                {'1': {'1': None, '2': None}, '2': {'1': None}, None: {None: None}},
            ),
            (
                [generate_ssd("version"), generate_ssd("sth_unexpected")],
                [gen_plan("r1", specifications={})],
                {'1': {None: None}, '2': {None: None}, None: {None: None}},
            ),
            (
                [generate_ssd("version"), generate_ssd("app_zone"), generate_ssd("sth_unexpected")],
                [gen_plan("r1", specifications={})],
                {'1': {'1': {None: None}, '2': {None: None}}, '2': {'1': {None: None}}, None: {None: {None: None}}},
            ),
        ],
    )
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_get_grouped_spec_values(
        self,
        mock_get_plans,
        bk_plan_r1_v1,
        bk_plan_r1_v2,
        bk_plan_r2_v1,
        bk_service_r1,
        service_ssd_list,
        extra_plans,
        expected,
    ):
        mock_get_plans.return_value = [bk_plan_r1_v1, bk_plan_r1_v2, bk_plan_r2_v1, *extra_plans]
        bk_service_r1.specifications = service_ssd_list

        helper = ServiceSpecificationHelper.from_service(bk_service_r1)

        # should not raise exceptions
        specs = helper.get_grouped_spec_values()
        assert specs == expected

    @pytest.mark.parametrize(
        "service_ssd_list, expected",
        [
            ([generate_ssd("version", recommended_value="1")], {"version": "1"}),
            (
                [generate_ssd("version", recommended_value="1"), generate_ssd("app_zone", recommended_value="2")],
                {"version": "1", "app_zone": "2"},
            ),
            (
                [
                    generate_ssd("version", recommended_value="1"),
                    generate_ssd("app_zone", recommended_value="unexpected"),
                ],
                {"version": "1", "app_zone": None},
            ),
            ([generate_ssd("version", recommended_value="unexpected")], {"version": None}),
            (
                [generate_ssd("version", recommended_value="1"), generate_ssd("unexpected", recommended_value="abc")],
                {"version": "1", "unexpected": None},
            ),
            (
                [
                    generate_ssd("version", recommended_value="unexpected"),
                    generate_ssd("app_zone", recommended_value="2"),
                ],
                {"version": None, "app_zone": None},
            ),
        ],
    )
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_get_recommended_spec(
        self, mock_get_plans, bk_plan_r1_v1, bk_plan_r1_v2, bk_plan_r2_v1, bk_service_r1, service_ssd_list, expected
    ):
        mock_get_plans.return_value = [bk_plan_r1_v1, bk_plan_r1_v2, bk_plan_r2_v1]
        bk_service_r1.specifications = service_ssd_list

        helper = ServiceSpecificationHelper.from_service(bk_service_r1)
        assert helper.get_recommended_spec() == expected

    @pytest.mark.parametrize(
        "service_ssd_list, plans, expected",
        [
            ([generate_ssd("version")], [gen_plan("", {"version": "1"})], [["1"]]),
            ([generate_ssd("unexpected")], [gen_plan("", {"version": "1"})], [[None]]),
            (
                [generate_ssd("foo"), generate_ssd("bar"), generate_ssd("baz")],
                [gen_plan("", {"foo": "1", "bar": "2", "baz": "3"})],
                [['1', '2', '3']],
            ),
            (
                [generate_ssd("foo"), generate_ssd("bar"), generate_ssd("baz")],
                [
                    gen_plan("", {"foo": "1", "bar": "2"}),
                    gen_plan(
                        "",
                        {"foo": "1", "baz": "3"},
                    ),
                    gen_plan(
                        "",
                        {"foo": "1"},
                    ),
                    gen_plan(
                        "",
                        {"bar": "2"},
                    ),
                ],
                [
                    ["1", "2", None],
                    ["1", None, "3"],
                    ["1", None, None],
                    [None, "2", None],
                ],
            ),
        ],
    )
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_list_plans_spec_value(self, mock_get_plans, bk_service_r1, service_ssd_list, plans, expected):
        mock_get_plans.return_value = plans
        bk_service_r1.specifications = service_ssd_list
        helper = ServiceSpecificationHelper.from_service(bk_service_r1)
        assert helper.list_plans_spec_value() == expected

    @pytest.mark.parametrize(
        "service_ssd_list, data, expected",
        [
            ([generate_ssd("version")], {"version": "1"}, {"version": "1"}),
            ([generate_ssd("unexpected")], {}, {"unexpected": None}),
            (
                [generate_ssd("foo"), generate_ssd("bar"), generate_ssd("baz")],
                {"foo": "1", "bar": "1", "baz": "1"},
                {"foo": "1", "bar": "1", "baz": "1"},
            ),
            (
                [generate_ssd("foo"), generate_ssd("bar"), generate_ssd("baz")],
                {"bar": "1", "baz": "1"},
                {"foo": None, "bar": "1", "baz": "1"},
            ),
            (
                [generate_ssd("foo"), generate_ssd("bar"), generate_ssd("baz")],
                {"foo": "1", "baz": "1"},
                {"foo": "1", "bar": None, "baz": "1"},
            ),
            (
                [generate_ssd("foo"), generate_ssd("bar"), generate_ssd("baz")],
                {"foo": "1", "bar": "1"},
                {"foo": "1", "bar": "1", "baz": None},
            ),
        ],
    )
    @mock.patch("paasng.dev_resources.servicehub.services.ServiceObj.get_plans")
    def test_validate_specs(self, mock_get_plans, bk_service_r1, service_ssd_list, data, expected):
        mock_get_plans.return_value = []
        bk_service_r1.specifications = service_ssd_list
        helper = ServiceSpecificationHelper.from_service(bk_service_r1)
        assert helper._validate_specs(data) == expected

    @pytest.mark.parametrize(
        "data, expected",
        [
            ([["a", "b", "c", "e"]], {'a': {'b': {'c': {'e': None}}}}),
            ([["a", "b"], ["a", "c"]], {'a': {'b': None, 'c': None}}),
            ([["a", "b"], ["a", "c"], ["d", "c"]], {'a': {'b': None, 'c': None}, 'd': {'c': None}}),
            # TODO: 确认以下测试用例是否符合预期?
            ([["a", "b", "c", "e"], ["d"]], {'a': {'b': {'c': {'e': None}}}, "d": None}),
            ([["a", "b"], ["a", None]], {'a': {'b': None, None: None}}),
        ],
    )
    def test_parse_spec_values_tree(self, data, expected):
        assert ServiceSpecificationHelper.parse_spec_values_tree(data) == expected
