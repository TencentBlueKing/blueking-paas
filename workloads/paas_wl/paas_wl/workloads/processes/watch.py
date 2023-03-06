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
from typing import Any, ClassVar, Dict, Generator, Iterable, List, Optional, Tuple, Type

from django.db import connection
from rest_framework.serializers import Serializer

from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.system_api.serializers import InstanceSerializer, ProcSpecsSerializer
from paas_wl.resources.kube_res.base import AppEntity
from paas_wl.resources.kube_res.exceptions import WatchKubeResourceError
from paas_wl.workloads.processes.models import Instance, Process
from paas_wl.workloads.processes.readers import instance_kmodel, process_kmodel

logger = logging.getLogger(__name__)


def watch_process_events(
    app: WlApp, timeout_seconds: int, rv_proc: Optional[int] = None, rv_inst: Optional[int] = None
) -> Generator[Dict, None, None]:
    """Create a watch stream to track app's all process related changes

    :param timeout_seconds: timeout seconds for generated event stream, recommended value: less than 120 seconds
    :param rv_proc: if given, only events with greater resource_version will be returned
    :param rv_inst: same as rv_proc, but for ProcInst type
    """
    kwargs = {'timeout_seconds': timeout_seconds}

    event_gens: List[Iterable] = [
        process_kmodel.watch_by_app(app, labels=None, resource_version=rv_proc, **kwargs),
        instance_kmodel.watch_by_app(app, labels=None, resource_version=rv_inst, **kwargs),
    ]
    # NOTE: Using of ThreadPoolExecutor/Multi-Threading may cause apiserver connections leak because every
    # `procinst_kmodel.watch_by_app` call will create a brand new kubernetes client object which holding a urllib3
    # connection pool manager.
    #
    # Use with caution.
    parallel_gen = ParallelChainedGenerator(event_gens)
    parallel_gen.start()
    for event in parallel_gen.iter_results():
        yield asdict(ProcWatchEvent.make_event(event))

    parallel_gen.close()


class ParallelChainedGenerator:
    """Consumes multiple generators in parallel"""

    def __init__(self, generators: List):
        self.queue: 'queue.Queue[Any]' = queue.Queue()
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

    def _consume_gen(self, gen: Generator):
        """Consumes generator and put result to queue"""
        try:
            for value in gen:
                self.queue.put(value)
        except WatchKubeResourceError as e:
            logger.warning('Watch resource error: %s', str(e))
            self.queue.put({'type': 'ERROR', 'message': str(e)})
        except Exception as e:
            logger.exception('Error while consuming generator: %s', str(e))
        finally:
            # Always close connection in every thread to avoid leaking of database connections
            connection.close()

    def iter_results(self) -> Generator[Any, None, None]:
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
        Process: ('process', ProcSpecsSerializer),
        Instance: ('instance', InstanceSerializer),
    }

    @classmethod
    def make_event(cls, raw_event: Dict) -> 'ProcWatchEvent':
        """Make an event instance from raw event object"""
        if raw_event['type'] == cls.type_error:
            return cls.make_error_event(raw_event)

        res_obj = raw_event['res_object']
        try:
            object_type, slz = cls.config[type(res_obj)]
        except KeyError:
            raise TypeError('Unsupported type {}'.format(type(res_obj)))
        return cls(
            type=raw_event['type'],
            object_type=object_type,
            object=dict(slz(res_obj).data),
            resource_version=res_obj.get_resource_version(),
        )

    @classmethod
    def make_error_event(cls, raw_event: Dict) -> 'ProcWatchEvent':
        """Make an error event"""
        return cls(type=cls.type_error, object_type='error', object=raw_event)
