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
"""Process controller"""
import logging
from typing import Dict, List, Tuple

from paas_wl.cnative.specs.constants import ApiVersion
from paas_wl.cnative.specs.models import default_bkapp_name
from paas_wl.cnative.specs.v1alpha1.bk_app import BkAppResource, ReplicasOverlay
from paas_wl.resources.base import crd
from paas_wl.resources.base.base import EnhancedApiClient
from paas_wl.resources.base.exceptions import ResourceMissing
from paas_wl.resources.base.kres import PatchType
from paas_wl.resources.utils.basic import get_client_by_app
from paasng.engine.constants import AppEnvName
from paasng.platform.applications.models import ModuleEnvironment

from .exceptions import ProcNotDeployed, ProcNotFoundInRes

logger = logging.getLogger(__name__)


class ProcReplicas:
    """Manage process's replicas

    :param env: The deployed env.
    """

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.wl_app = env.wl_app
        self.ns = self.wl_app.namespace
        self.res_name = default_bkapp_name(self.env)

    def get(self, proc_type: str) -> int:
        """Get the replicas count by process type"""
        return self.get_with_overlay(proc_type)[0]

    def get_with_overlay(self, proc_type: str) -> Tuple[int, bool]:
        """Get the replicas count by process type, with an extra field: "in_overlay"

        :return: (replicas, whether replicas was defined in "envOverlay")
        """
        with get_client_by_app(self.env.wl_app) as client:
            bkapp_res = self._get_bkapp_res(client)

        counts = ReplicasReader(bkapp_res).read_all(AppEnvName(self.env.environment))
        if proc_type not in counts:
            raise ProcNotFoundInRes(proc_type)
        return counts[proc_type]

    def scale(self, proc_type: str, count: int):
        """Scale replicas by process type

        :param proc_type: Process type, such as "web", "worker" etc.
        :param count: Replica count
        :raise: `ValueError` when count is invalid
        :raise: `ProcNotDeployed` when app is not deployed yet
        :raise: `ProcNotFoundInRes` when process can not be found
        """
        if count < 0:
            raise ValueError('count must greater than or equal to 0')

        with get_client_by_app(self.wl_app) as client:
            bkapp_res = self._get_bkapp_res(client)
            self._validate_proc_type(bkapp_res, proc_type)

            # Backward compatible: when "envOverlay" is None
            if overlay := bkapp_res.spec.envOverlay:
                replicas_overlay = overlay.replicas or []
            else:
                replicas_overlay = []

            self._set_process(replicas_overlay, self.env.environment, proc_type, count)

            patch_body = {'spec': {'envOverlay': {'replicas': [r.dict() for r in replicas_overlay]}}}
            # "strategic json merge" is not available for CRD resources, use
            # "json merge" to replace the entire array.
            crd.BkApp(client).patch(self.res_name, namespace=self.ns, body=patch_body, ptype=PatchType.MERGE)

    def _get_bkapp_res(self, client: EnhancedApiClient) -> BkAppResource:
        """Get app model resource from cluster"""
        try:
            # TODO 确定多版本交互后解除版本锁定
            data = crd.BkApp(client, api_version=ApiVersion.V1ALPHA1).get(self.res_name, namespace=self.ns)
        except ResourceMissing:
            raise ProcNotDeployed(f'{self.env} not deployed')
        return BkAppResource(**data)

    @staticmethod
    def _validate_proc_type(bkapp_res: BkAppResource, proc_type: str):
        """Validate process type, check if it was defined in specification"""
        names = [p.name for p in bkapp_res.spec.processes]
        if proc_type not in names:
            raise ProcNotFoundInRes(proc_type)

    @staticmethod
    def _set_process(data: List[ReplicasOverlay], env_name: str, proc_type: str, count: int):
        """Update a list of overlay objects, insert or update process entry"""
        found = False
        for r in data:
            if r.envName == env_name and r.process == proc_type:
                r.count = count
                found = True
        if not found:
            data.append(ReplicasOverlay(envName=env_name, process=proc_type, count=count))


class ReplicasReader:
    """Read "replicas" from app model resource object

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self, env_name: AppEnvName) -> Dict[str, Tuple[int, bool]]:
        """Read all replicas count defined

        :param env_name: Environment name
        :return: A dict contains replicas for all processes, value format:
            (replicas, whether replicas was defined in "envOverlay")
        """
        # Read value from main configuration
        results = {p.name: (p.replicas, False) for p in self.res.spec.processes}

        # Read value from "envOverlay"
        if overlay := self.res.spec.envOverlay:
            replicas_overlay = overlay.replicas or []
        else:
            replicas_overlay = []

        for r in replicas_overlay:
            # Only add entries which were defined in main configuration
            if r.envName == env_name.value and r.process in results:
                results[r.process] = (r.count, True)
        return results
