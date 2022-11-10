# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, cast

from paas_wl.platform.applications.constants import EngineAppType
from paas_wl.platform.applications.models.managers.app_res_ver import AppResVerManager
from paas_wl.resources.base.kres import KPod
from paas_wl.resources.kube_res.base import AppEntityReader, ResourceList
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.processes.constants import PROCESS_NAME_KEY
from paas_wl.workloads.processes.managers import AppProcessManager
from paas_wl.workloads.processes.models import Instance, Process

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import App


class ProcessAPIAdapter:
    """Data adapter for Process"""

    @staticmethod
    def get_kube_pod_selector(app: 'App', process_type: str) -> Dict[str, str]:
        """Return pod selector dict, useful for construct Deployment body and related Service"""
        if app.type == EngineAppType.CLOUD_NATIVE:
            return {PROCESS_NAME_KEY: process_type}

        proc = AppProcessManager(app).assemble_process(process_type)
        return {"pod_selector": AppResVerManager(app).curr_version.deployment(proc).pod_selector}


class ProcessReader(AppEntityReader[Process]):
    """Manager for ProcSpecs"""

    def get_by_type(self, app: 'App', type: str) -> 'Process':
        """Get object by process type"""
        labels = ProcessAPIAdapter.get_kube_pod_selector(app, type)
        objs = self.list_by_app(app, labels=labels)
        if objs:
            return objs[0]
        raise AppEntityNotFound(f'No processes can be found with type={type}')


process_kmodel = ProcessReader(Process)


class InstanceReader(AppEntityReader[Instance]):
    """Customized reader for ProcInstance"""

    def list_by_process_type(self, app: 'App', process_type: str) -> List[Instance]:
        """List instances by process type"""
        labels = ProcessAPIAdapter.get_kube_pod_selector(app, process_type)
        return self.list_by_app(app, labels=labels)

    def list_by_app_with_meta(self, app: 'App', labels: Optional[Dict] = None) -> ResourceList[Instance]:
        """Overwrite original method to remove slugbuilder pods"""
        resources = super().list_by_app_with_meta(app, labels=labels)
        if app.type == EngineAppType.CLOUD_NATIVE:
            resources.items = list(self.filter_cnative_insts(app, resources.items))
        else:
            # Ignore instances with no valid "release_version" label
            resources.items = [r for r in resources.items if r.version > 0]
        return resources

    def get_logs(self, obj: Instance, tail_lines: Optional[int] = None, **kwargs):
        """Get logs from kubernetes api"""
        with self.kres(obj.app) as kres_client:
            kres_client = cast(KPod, kres_client)
            return kres_client.get_log(
                name=obj.name,
                namespace=obj.app.namespace,
                tail_lines=tail_lines,
                container=obj.app.scheduler_safe_name,
                **kwargs,
            )

    @staticmethod
    def filter_cnative_insts(app: 'App', items: Iterable[Instance]) -> Iterable[Instance]:
        """Filter instances for cloud-native applications, remove hooks and other
        unrelated items.
        """
        for inst in items:
            if inst.name.startswith('pre-release-hook'):
                continue
            yield inst


instance_kmodel = InstanceReader(Instance)
