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
from unittest import mock

import arrow
import pytest

from paas_wl.cnative.specs.constants import BKPAAS_DEPLOY_ID_ANNO_KEY
from paas_wl.cnative.specs.crd.bk_app import BkAppResource, BkAppStatus, MetaV1Condition
from paas_wl.cnative.specs.events import Event
from paas_wl.networking.entrance.addrs import Address, AddressType
from tests.paas_wl.cnative.specs.utils import create_cnative_deploy

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestMresDeploymentsViewSet:
    def test_list(self, api_client, bk_app, bk_module, bk_stag_env, bk_user):
        url = (
            "/svc_workloads/api/cnative/specs/applications/"
            f"{bk_app.code}/modules/{bk_module.name}/envs/{bk_stag_env.environment}/mres/deployments/"
        )

        dp = create_cnative_deploy(bk_stag_env, bk_user)
        response = api_client.get(url)

        assert response.data['count'] == 1
        assert response.data['previous'] is None
        assert response.data['next'] is None
        ret = response.data['results'][0]
        # django serializer 提供时区转换，因此不进行比较
        assert ret.pop('created') is not None
        assert ret.pop('updated') is not None
        assert ret == {
            'id': dp.pk,
            'application_id': str(bk_app.id),
            'environment_name': bk_stag_env.environment,
            'name': dp.name,
            'region': dp.region,
            'revision': dp.revision.pk,
            'status': dp.status,
            'reason': dp.reason,
            'message': dp.message,
            'last_transition_time': dp.last_transition_time,
            'operator': bk_user.username,
        }

    def test_create(self, api_client, bk_app, bk_module, bk_stag_env, with_wl_apps, bk_user):
        url = (
            "/svc_workloads/api/cnative/specs/applications/"
            f"{bk_app.code}/modules/{bk_module.name}/envs/{bk_stag_env.environment}/mres/deployments/"
        )

        create_cnative_deploy(bk_stag_env, bk_user)
        manifest = {
            "apiVersion": "paas.bk.tencent.com/v1alpha2",
            "kind": "BkApp",
            "metadata": {"name": bk_app.code},
            "spec": {
                "build": {
                    "image": "strm/helloworld-http",
                    "imagePullPolicy": "IfNotPresent",
                },
                "configuration": {"env": []},
                "hooks": {"preRelease": {"args": ["-c", "echo hello2"], "command": ["/bin/sh"]}},
                "processes": [
                    {
                        "args": [],
                        "command": [],
                        "cpu": "250m",
                        "memory": "256Mi",
                        "name": "web",
                        "replicas": 2,
                        "targetPort": 80,
                    }
                ],
            },
        }
        # Mock out the interactions with k8s cluster
        with mock.patch("paasng.engine.deploy.release.operator.apply_bkapp_to_k8s", return_value=manifest), mock.patch(
            'paasng.engine.deploy.release.operator.AppModelDeployStatusPoller.start',
            return_value=None,
        ), mock.patch("paasng.engine.deploy.release.operator.svc_disc"):
            response = api_client.post(url, data={"manifest": manifest})

        assert response.status_code == 200
        assert response.data['apiVersion'] == "paas.bk.tencent.com/v1alpha2"
        assert response.data['kind'] == "BkApp"
        assert response.data['metadata']['name'] == bk_app.code
        assert response.data['spec'] is not None


class TestMresStatusViewSet:
    def test_retrieve(self, api_client, bk_app, bk_module, bk_stag_env, with_wl_apps, bk_user):
        url = (
            "/svc_workloads/api/cnative/specs/applications/"
            f"{bk_app.code}/modules/{bk_module.name}/envs/{bk_stag_env.environment}/mres/status/"
        )

        dp = create_cnative_deploy(bk_stag_env, bk_user)
        bkapp_res = BkAppResource(
            apiVersion="paas.bk.tencent.com/v1alpha2",
            kind="BkApp",
            metadata={
                "name": bk_app.code,
                "annotations": {BKPAAS_DEPLOY_ID_ANNO_KEY: dp.pk},
            },
            spec={
                "build": {
                    "image": "strm/helloworld-http",
                    "imagePullPolicy": "IfNotPresent",
                },
                "configuration": {"env": []},
                "hooks": {"preRelease": {"args": ["-c", "echo hello2"], "command": ["/bin/sh"]}},
                "processes": [
                    {
                        "args": [],
                        "command": [],
                        "cpu": "250m",
                        "memory": "256Mi",
                        "name": "web",
                        "replicas": 2,
                        "targetPort": 80,
                    }
                ],
            },
            status=BkAppStatus(
                conditions=[
                    MetaV1Condition(
                        type="AppAvailable",
                        status="True",
                        reason="AppAvailable",
                        message="",
                    ),
                    MetaV1Condition(type="AppProgressing", status="True", reason="NewRevision", message=""),
                ]
            ),
        )
        events = [
            Event(
                name="pre-release-hook-14.1756b63cec29a836",
                type="Normal",
                reason="Started",
                count=1,
                message="Started container hook",
                source_component="kubelet",
                involved_object=None,
                first_seen=arrow.get("2023-04-17 19:44:43").datetime,
                last_seen=arrow.get("2023-04-17 19:44:43").datetime,
            )
        ]
        with mock.patch(
            "paas_wl.cnative.specs.views_enduser.get_mres_from_cluster", return_value=bkapp_res
        ), mock.patch('paas_wl.cnative.specs.views_enduser.list_events', return_value=events,), mock.patch(
            'paas_wl.cnative.specs.views_enduser.get_exposed_url',
            return_value=Address(type=AddressType.SUBDOMAIN, url="http://example.com").to_exposed_url(),
        ):
            response = api_client.get(url)
            excepted = {
                'deployment': {
                    'deploy_id': dp.pk,
                    'status': 'ready',
                    'reason': None,
                    'message': None,
                    'last_transition_time': None,
                    'operator': bk_user.username,
                },
                'ingress': {'url': 'http://example.com'},
                'conditions': [
                    {'type': 'AppAvailable', 'status': 'True', 'reason': 'AppAvailable', 'message': ''},
                    {'type': 'AppProgressing', 'status': 'True', 'reason': 'NewRevision', 'message': ''},
                ],
                'events': [
                    {
                        'name': 'pre-release-hook-14.1756b63cec29a836',
                        'type': 'Normal',
                        'reason': 'Started',
                        'count': '1',
                        'message': 'Started container hook',
                        'source_component': 'kubelet',
                        'first_seen': '2023-04-18 03:44:43',
                        'last_seen': '2023-04-18 03:44:43',
                    }
                ],
            }

            # django serializer 提供时区转换，因此不进行比较
            assert response.data['deployment'].pop('created') is not None
            assert response.data == excepted
