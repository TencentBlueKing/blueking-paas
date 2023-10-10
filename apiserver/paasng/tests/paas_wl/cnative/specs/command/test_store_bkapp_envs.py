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
from typing import Dict, List, Optional

import pytest
from django.core.management import CommandError, call_command

from paas_wl.cnative.specs.crd.bk_app import EnvVar, EnvVarOverlay
from paas_wl.cnative.specs.models import AppModelResource, create_app_resource
from paasng.platform.engine.models import ConfigVar

pytestmark = pytest.mark.django_db(databases=['default', 'workloads'])


@pytest.mark.parametrize(
    "args, exception_type, expected_message",
    [
        ({}, CommandError, "can't get bkapp with given params"),
        (
            {"app_code": "foo", "cluster_name": "bar"},
            CommandError,
            "'cluster_name' and 'app_code' can't be used together.",
        ),
        ({"cluster_name": "bar"}, CommandError, "'region' is required when providing 'cluster_name'"),
        ({"app_code": "foo", "module_name": "bar"}, CommandError, "can't get bkapp with given params"),
        ({"cluster_name": "foo", "region": "bar"}, CommandError, "can't get bkapp with given params"),
    ],
)
def test_invalid_params(args, exception_type, expected_message):
    with pytest.raises(exception_type) as exp:
        call_command("store_bkapp_envs", **args)
    assert str(exp.value) == expected_message


def init_model_resource(bk_app, bk_module, resource_name):
    """Initialize the app model resource"""
    resource = create_app_resource(
        # Use Application code as default resource name
        name=resource_name,
        image='nginx:latest',
        command=None,
        args=None,
        target_port=None,
    )
    return AppModelResource.objects.create_from_resource(bk_app.region, bk_app.id, bk_module.id, resource)


def make_spec_updater(envs: Optional[List[EnvVar]] = None, env_overlay: Optional[List[EnvVarOverlay]] = None):
    def updater(spec: Dict):
        if envs is not None:
            spec["configuration"]["env"] = [e.dict() for e in envs]
        if env_overlay is not None:
            if "envOverlay" not in spec:
                spec["envOverlay"] = {}
            spec["envOverlay"]["envVariables"] = [e.dict() for e in env_overlay]

    return updater


@pytest.mark.parametrize(
    "spec_updator, expected",
    [
        (make_spec_updater(), []),
        (
            make_spec_updater([EnvVar(name="foo", value="bar")]),
            [
                ("FOO", "bar", "stag"),
                ("FOO", "bar", "prod"),
            ],
        ),
        (
            make_spec_updater(
                [EnvVar(name="foo", value="bar")], [EnvVarOverlay(name="foo", value="baz", envName="stag")]
            ),
            [
                ("FOO", "baz", "stag"),
                ("FOO", "bar", "prod"),
            ],
        ),
        (
            make_spec_updater(
                [EnvVar(name="foo", value="bar")], [EnvVarOverlay(name="Foo", value="baz", envName="stag")]
            ),
            [
                ("Foo", "baz", "stag"),
                ("FOO", "bar", "prod"),
            ],
        ),
    ],
)
def test_handle(bk_cnative_app, bk_module, bk_stag_wl_app, spec_updator, expected):
    model_res = init_model_resource(bk_cnative_app, bk_module, "foo")
    revision = model_res.revision
    spec_updator(revision.json_value["spec"])
    revision.save()

    call_command("store_bkapp_envs", app_code=bk_cnative_app.code, module_name=bk_module.name, dry_run=False)

    assert ConfigVar.objects.filter(module=bk_module).count() == len(expected)
    for key, value, env_name in expected:
        assert ConfigVar.objects.get(key=key, environment=bk_module.get_envs(env_name)).value == value
