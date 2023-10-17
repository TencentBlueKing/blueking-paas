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
from paas_wl.bk_app.cnative.specs.apis import ObjectMetadata
from paas_wl.bk_app.cnative.specs.constants import ApiVersion, ResQuotaPlan
from paas_wl.bk_app.cnative.specs.converter import BkAppResourceConverter
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppBuildConfig, BkAppProcess, BkAppResource, BkAppSpec
from paas_wl.bk_app.cnative.specs.models import create_app_resource


class TestBkAppResourceConverter:
    def test_do_nothing(self):
        obj = create_app_resource('foo-app', 'nginx:latest')
        assert BkAppResourceConverter(obj).convert() == (obj, False, False)

    def test_normal(self):
        obj = BkAppResource(
            apiVersion=ApiVersion.V1ALPHA1,
            metadata=ObjectMetadata(name='foo'),
            spec=BkAppSpec(
                processes=[
                    BkAppProcess(
                        name='web',
                        image='nginx:latest',
                        command=[],
                        args=[],
                        cpu='2000m',
                        memory='1200Mi',
                        targetPort=80,
                    )
                ],
            ),
        )
        excepted = BkAppResource(
            apiVersion=ApiVersion.V1ALPHA2,
            metadata=ObjectMetadata(name='foo'),
            spec=BkAppSpec(
                build=BkAppBuildConfig(
                    image='nginx',
                ),
                processes=[
                    BkAppProcess(
                        name='web',
                        image=None,
                        command=[],
                        args=[],
                        resQuotaPlan=ResQuotaPlan.P_2C2G,
                        targetPort=80,
                        cpu='',
                        memory='',
                    )
                ],
            ),
        )
        assert BkAppResourceConverter(obj).convert() == (excepted, True, True)

    def test_convert_resQuotaPlan_only(self):
        obj = BkAppResource(
            apiVersion=ApiVersion.V1ALPHA1,
            metadata=ObjectMetadata(name='foo'),
            spec=BkAppSpec(
                processes=[
                    BkAppProcess(
                        name='web',
                        image='nginx:latest',
                        command=[],
                        args=[],
                        cpu='2000m',
                        memory='1200Mi',
                        targetPort=80,
                    ),
                    BkAppProcess(
                        name='worker',
                        image='busybox:latest',
                        command=['/bin/sh', '-c'],
                        args=['echo hello'],
                        cpu='2000m',
                        memory='1024Mi',
                    ),
                ],
            ),
        )
        excepted = BkAppResource(
            apiVersion=ApiVersion.V1ALPHA1,
            metadata=ObjectMetadata(name='foo'),
            spec=BkAppSpec(
                processes=[
                    BkAppProcess(
                        name='web',
                        image='nginx:latest',
                        command=[],
                        args=[],
                        resQuotaPlan=ResQuotaPlan.P_2C2G,
                        cpu='',
                        memory='',
                        targetPort=80,
                    ),
                    BkAppProcess(
                        name='worker',
                        image='busybox:latest',
                        command=['/bin/sh', '-c'],
                        args=['echo hello'],
                        resQuotaPlan=ResQuotaPlan.P_2C1G,
                        cpu='',
                        memory='',
                    ),
                ],
            ),
        )
        assert BkAppResourceConverter(obj).convert() == (excepted, True, False)
