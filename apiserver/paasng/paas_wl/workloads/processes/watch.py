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
import logging
import queue
import threading
from dataclasses import asdict, dataclass
from typing import Any, ClassVar, Dict, Generator, List, Optional, Tuple, Type, Union

from django.db import connection
from django.utils.functional import cached_property
from rest_framework.serializers import Serializer

from paas_wl.networking.ingress.utils import get_service_dns_name
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.kube_res.base import AppEntity, WatchEvent
from paas_wl.resources.kube_res.exceptions import WatchKubeResourceError
from paas_wl.workloads.processes.controllers import take_processes_snapshot
from paas_wl.workloads.processes.drf_serializers import InstanceForDisplaySLZ, ListWatcherRespSLZ, ProcessForDisplaySLZ
from paas_wl.workloads.processes.entities import Instance, Process
from paas_wl.workloads.processes.readers import ProcessAPIAdapter, instance_kmodel, process_kmodel
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)
_EVENT_TYPE = WatchEvent[Union[Process, Instance]]


class ProcessInstanceListWatcher:
    """ListWatcher for Process(Deployment) & Instance(Pod) in given env"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    @cached_property
    def wl_app(self) -> WlApp:
        return self.env.wl_app

    def list(self, release_id: Optional[str] = None) -> Dict:
        """Build a structured data including processes and instances

        :param release_id: if given, include instances created by given release only
        :return: A dict with "processes" and "instances"
        """
        # TODO: 支持根据命名空间 list
        processes_status = take_processes_snapshot(self.env)

        # Get extra infos
        proc_extra_infos = []
        for proc_spec in processes_status.processes:
            proc_extra_infos.append(
                {
                    'type': proc_spec.type,
                    # TODO: 云原生应用添加 proc_command 字段
                    'command': proc_spec.runtime.proc_command,
                    'cluster_link': f'http://{get_service_dns_name(proc_spec.app, proc_spec.type)}',
                }
            )

        insts = [inst for proc in processes_status.processes for inst in proc.instances]
        # Filter instances if required
        if release_id:
            release = self.wl_app.release_set.get(pk=release_id)
            insts = [inst for inst in insts if inst.version == release.version]

        result = {
            'processes': {
                'items': processes_status.processes,
                'extra_infos': proc_extra_infos,
                'metadata': {'resource_version': processes_status.processes_resource_version},
            },
            'instances': {
                'items': insts,
                'metadata': {'resource_version': processes_status.instances_resource_version},
            },
        }
        return ListWatcherRespSLZ(result).data

    def watch(
        self, timeout_seconds: int, rv_proc: Optional[int] = None, rv_inst: Optional[int] = None
    ) -> Generator['ProcWatchEvent', None, None]:
        """Create a watch stream to track app's all process related changes

        :param timeout_seconds: timeout seconds for generated event stream, recommended value: less than 120 seconds
        :param rv_proc: if given, only events with greater resource_version will be returned
        :param rv_inst: same as rv_proc, but for ProcInst type
        """
        # TODO: 支持根据命名空间 watch
        event_gens: List = [
            process_kmodel.watch_by_app(
                self.wl_app,
                labels=ProcessAPIAdapter.app_selector(self.wl_app),
                resource_version=rv_proc,
                timeout_seconds=timeout_seconds,
            ),
            instance_kmodel.watch_by_app(
                self.wl_app,
                labels=ProcessAPIAdapter.app_selector(self.wl_app),
                resource_version=rv_inst,
                timeout_seconds=timeout_seconds,
            ),
        ]
        # NOTE: Using of ThreadPoolExecutor/Multi-Threading may cause apiserver connections leak because every
        # `procinst_kmodel.watch_by_app` call will create a brand new kubernetes client object which holding a urllib3
        # connection pool manager.
        #
        # Use with caution.
        parallel_gen = ParallelChainedGenerator(event_gens)
        parallel_gen.start()
        for event in parallel_gen.iter_results():
            yield ProcWatchEvent.make_event(event)

        parallel_gen.close()


class ParallelChainedGenerator:
    """Consumes multiple generators in parallel"""

    def __init__(self, generators: List):
        self.queue: queue.Queue = queue.Queue()
        self.generators = generators
        self.tasks: List = []
        self._started = False

    def start(self):
        """Start current generator"""
        for gen in self.generators:
            task = threading.Thread(target=self._consume_gen, args=(gen,))
            task.setDaemon(True)
            task.start()
            self.tasks.append(task)

        self._started = True

    def _consume_gen(self, gen: Generator[WatchEvent[Any], None, None]):
        """Consumes generator and put result to queue"""
        try:
            for value in gen:
                self.queue.put(value)
        except WatchKubeResourceError as e:
            logger.warning('Watch resource error: %s', str(e))
            self.queue.put(WatchEvent(type="ERROR", message=str(e)))
        except Exception as e:
            logger.exception('Error while consuming generator: %s', str(e))
        finally:
            # Always close connection in every thread to avoid leaking of database connections
            connection.close()

    def iter_results(self) -> Generator[WatchEvent[Any], None, None]:
        """yield results as a generator"""
        if not self._started:
            raise ValueError('current generator is not started yet')

        while True:
            try:
                item = self.queue.get(timeout=0.5)
            except queue.Empty:
                pass
            else:
                yield item
                self.queue.task_done()

            all_task_finished = all(not task.is_alive() for task in self.tasks)
            if all_task_finished and self.queue.empty():
                break

    def close(self):
        pass


@dataclass
class ProcWatchEvent:
    """Process related watch event object"""

    # Instance variables
    type: str
    object_type: str
    object: Dict
    resource_version: Optional[str] = None

    # Class variables
    type_error: ClassVar[str] = 'ERROR'
    config: ClassVar[Dict[Type[AppEntity], Tuple[str, Serializer]]] = {
        Process: ('process', ProcessForDisplaySLZ),
        Instance: ('instance', InstanceForDisplaySLZ),
    }

    @classmethod
    def make_event(cls, raw_event: _EVENT_TYPE) -> 'ProcWatchEvent':
        """Make an event instance from raw event object"""
        if raw_event.type == cls.type_error:
            return cls.make_error_event(raw_event)

        res_obj = raw_event.res_object
        assert res_obj is not None
        try:
            object_type, slz = cls.config[type(res_obj)]
        except KeyError:
            raise TypeError('Unsupported type {}'.format(type(res_obj)))

        return cls(
            type=raw_event.type,
            object_type=object_type,
            object=dict(slz(res_obj).data),
            resource_version=res_obj.get_resource_version(),
        )

    @classmethod
    def make_error_event(cls, raw_event: _EVENT_TYPE) -> 'ProcWatchEvent':
        """Make an error event"""
        return cls(type=cls.type_error, object_type='error', object=asdict(raw_event))
