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
import copy
import logging
from typing import Dict, List, Optional, Tuple

from paas_wl.bk_app.cnative.specs.constants import ApiVersion
from paas_wl.bk_app.cnative.specs.crd.bk_app import AutoscalingOverlay, BkAppResource, ReplicasOverlay
from paas_wl.bk_app.cnative.specs.models import generate_bkapp_name
from paas_wl.infras.resources.base import crd
from paas_wl.infras.resources.base.base import EnhancedApiClient
from paas_wl.infras.resources.base.exceptions import ResourceMissing
from paas_wl.infras.resources.base.kres import PatchType
from paas_wl.infras.resources.utils.basic import get_client_by_app
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName

from .exceptions import ProcNotDeployed, ProcNotFoundInRes

logger = logging.getLogger(__name__)


class BkAppProcScaler:
    """Scale the bkapp's processes by updating the resource in cluster. Support fixed replicas
    and autoscaling.

    :param env: The deployed env.
    """

    def __init__(self, env: ModuleEnvironment):
        self.env = env
        self.wl_app = env.wl_app
        self.ns = self.wl_app.namespace
        self.res_name = generate_bkapp_name(self.env)

    def get_replicas(self, proc_type: str) -> int:
        """Get the replicas count by process type.

        :raises ProcNotFoundInRes: when the process can not be found.
        :return: replicas
        """
        with get_client_by_app(self.env.wl_app) as client:
            bkapp_res = self._get_bkapp_res(client)

        counts = ReplicasReader(bkapp_res).read_all(AppEnvName(self.env.environment))
        if proc_type not in counts:
            raise ProcNotFoundInRes(proc_type)
        return counts[proc_type][0]

    def set_replicas(self, proc_type: str, count: int):
        """Set the replicas to a fixed value by process type.

        :param proc_type: Process type, such as "web", "worker" etc.
        :param count: Replica count
        :raise: `ValueError` when count is invalid
        :raise: `ProcNotDeployed` when app is not deployed yet
        :raise: `ProcNotFoundInRes` when process can not be found
        """
        if count < 0:
            raise ValueError("count must greater than or equal to 0")

        with get_client_by_app(self.wl_app) as client:
            bkapp_res = self._get_bkapp_res(client)
            self._validate_proc_type(bkapp_res, proc_type)

            # Backward compatible: when "envOverlay" is None
            if overlay := bkapp_res.spec.envOverlay:
                replicas_overlay = overlay.replicas or []
            else:
                replicas_overlay = []

            self._set_process(replicas_overlay, self.env.environment, proc_type, count)

            patch_body = {"spec": {"envOverlay": {"replicas": [r.dict() for r in replicas_overlay]}}}
            # "strategic json merge" is not available for CRD resources, use
            # "json merge" to replace the entire array.
            crd.BkApp(client).patch(self.res_name, namespace=self.ns, body=patch_body, ptype=PatchType.MERGE)

    def get_autoscaling(self, proc_type: str) -> Optional[Dict]:
        """Get the autoscaling config for the given process type.

        NOTE: The return value is currently only used in unit tests, it's type may
        change in the future.

        :raises ProcNotFoundInRes: when the process can not be found.
        :return: None when autoscaling is not enabled.
        """
        with get_client_by_app(self.wl_app) as client:
            bkapp_res = self._get_bkapp_res(client)
            configs = AutoscalingReader(bkapp_res).read_all(AppEnvName(self.env.environment))
            if proc_type not in configs:
                raise ProcNotFoundInRes(proc_type)

            return configs[proc_type][0]

    def set_autoscaling(self, proc_type: str, enabled: bool, config: Optional[AutoscalingConfig]):
        """Set the auto-scaling config by process type.

        :param proc_type: Process type, such as "web", "worker" etc.
        :param enabled: Whether enable auto-scaling.
        :param config: The auto-scaling config data, allow `None` when enabled is False.
        :raise: `ProcNotDeployed` when app is not deployed yet
        :raise: `ProcNotFoundInRes` when process can not be found
        """
        with get_client_by_app(self.wl_app) as client:
            bkapp_res = self._get_bkapp_res(client)
            self._validate_proc_type(bkapp_res, proc_type)

            # Backward compatible: when "envOverlay" is None
            if overlay := bkapp_res.spec.envOverlay:
                autoscaling_overlay = overlay.autoscaling or []
            else:
                autoscaling_overlay = []

            items = self._set_autoscaling_overlay(
                autoscaling_overlay, self.env.environment, proc_type, enabled, config
            )

            patch_body = {"spec": {"envOverlay": {"autoscaling": [r.dict() for r in items]}}}
            crd.BkApp(client).patch(self.res_name, namespace=self.ns, body=patch_body, ptype=PatchType.MERGE)

    def _get_bkapp_res(self, client: EnhancedApiClient) -> BkAppResource:
        """Get app model resource from cluster"""
        try:
            data = crd.BkApp(client, api_version=ApiVersion.V1ALPHA2).get(self.res_name, namespace=self.ns)
        except ResourceMissing:
            raise ProcNotDeployed(f"{self.env} not deployed")
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

    @staticmethod
    def _set_autoscaling_overlay(
        data: List[AutoscalingOverlay],
        env_name: str,
        proc_type: str,
        enabled: bool,
        config: Optional[AutoscalingConfig],
    ) -> List[AutoscalingOverlay]:
        """Update a list of the overlay objects, modify the entry which belongs to the
        process, return the updated list.
        """
        # Handle disable
        if not enabled:
            return [ao for ao in data if not (ao.envName == env_name and ao.process == proc_type)]

        # Handle enable
        assert config is not None, "Config can not be None when enabled is True"
        results: List[AutoscalingOverlay] = []
        found = False
        for item in data:
            # Avoid updating the original object
            item_copy = copy.copy(item)
            if item_copy.envName == env_name and item_copy.process == proc_type:
                item_copy.minReplicas = config.min_replicas
                item_copy.maxReplicas = config.max_replicas
                item_copy.policy = config.policy
                # Other properties such as "metrics" are not supported yet
                found = True
            results.append(item_copy)

        if not found:
            results.append(
                AutoscalingOverlay(
                    envName=env_name,
                    process=proc_type,
                    minReplicas=config.min_replicas,
                    maxReplicas=config.max_replicas,
                    policy=config.policy,
                )
            )
        return results


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


class AutoscalingReader:
    """Read "autoscaling" from an app model resource object.

    :param res: App model resource object
    """

    def __init__(self, res: BkAppResource):
        self.res = res

    def read_all(self, env_name: AppEnvName) -> Dict[str, Tuple[Optional[Dict], bool]]:
        """Read all autoscaling config defined

        :param env_name: Environment name
        :return: Dict[name of process, (config, whether the config was defined in "envOverlay")]
        """
        # Read value from main configuration
        results = {
            p.name: (
                {
                    "min_replicas": c.minReplicas,
                    "max_replicas": c.maxReplicas,
                    "policy": c.policy,
                }
                if (c := p.autoscaling)
                else None,
                False,
            )
            for p in self.res.spec.processes
        }

        # Read value from "envOverlay"
        if overlay := self.res.spec.envOverlay:
            autoscaling_overlay = overlay.autoscaling or []
        else:
            autoscaling_overlay = []

        for r in autoscaling_overlay:
            # Only add entries which were defined in main configuration
            if r.envName == env_name.value and r.process in results:
                results[r.process] = (
                    {
                        "min_replicas": r.minReplicas,
                        "max_replicas": r.maxReplicas,
                        "policy": r.policy,
                    },
                    True,
                )
        return results
