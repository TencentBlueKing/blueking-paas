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
from textwrap import dedent

import pytest

from paas_wl.platform.applications.models import WlApp
from paas_wl.workloads.processes.constants import ProbeType
from paas_wl.workloads.processes.models import ProcessProbe
from paasng.extensions.declarative.handlers import AppDescriptionHandler

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_saas_probes(bk_deployment):
    """验证 saas 应用探针对象 ProcessProbe 成功创建 """
    yaml_content = dedent(
        '''
        spec_version: 2
        app_version: "1.0"
        app:
            region: default
            bk_app_code: "foo-app"
            bk_app_name: 默认应用名称
            bk_app_name_en: default-app-name
        modules:
            default:
                source_dir: src/frontend
                language: NodeJS
                processes:
                    web:
                        command: npm run server
                        plan: 4C1G5R
                        replicas: 2
                        probes:
                            liveness:
                                exec:
                                    command:
                                    - cat
                                    - /tmp/healthy
                            readiness:
                                tcp_socket:
                                    port: ${PORT}
        '''
    )
    # bk_deployment 外键对象未创建，补全
    name = bk_deployment.app_environment.engine_app.name
    region = bk_deployment.app_environment.engine_app.region
    wlapp = WlApp.objects.create(name=name, region=region)

    fp = io.StringIO(yaml_content)
    AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
    liveness_probe: ProcessProbe = ProcessProbe.objects.get(
        app=wlapp, process_type='web', probe_type=ProbeType.LIVENESS
    )
    readiness_probe: ProcessProbe = ProcessProbe.objects.get(
        app=wlapp, process_type='web', probe_type=ProbeType.READINESS
    )

    assert liveness_probe.check_mechanism
    assert liveness_probe.check_mechanism.exec.command == ['cat', '/tmp/healthy']

    assert readiness_probe.check_mechanism
    assert readiness_probe.check_mechanism.tcp_socket.port == "${PORT}"
