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

from paasng.engine.deploy.engine_svc import EngineDeployClient
from paasng.engine.processes.serializers import ProcessFilterQuerySLZ
from paasng.platform.applications.mixins import ApplicationCodeInPathMixin


class ProcessesFilterBackend:
    @staticmethod
    def filter(request, processes: Dict, view: ApplicationCodeInPathMixin) -> Dict:
        """根据参数过滤 processes 的内容"""

        serializer = ProcessFilterQuerySLZ(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not data["release_id"]:
            return processes

        env = view.get_env_via_path()
        client = EngineDeployClient(engine_app=env.engine_app)
        release_id = data["release_id"]
        release_version = client.get_release(str(release_id)).get('version', '')

        if not release_version:
            return processes

        instances = [i for i in processes['instances']['items'] if i["version"] == str(release_version)]
        processes['instances']['items'] = instances
        return processes
