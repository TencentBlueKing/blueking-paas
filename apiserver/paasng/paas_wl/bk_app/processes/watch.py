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
from typing import Any, Generator, List, Optional, Union

from django.db import connection
from django.utils.functional import cached_property

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.bk_app.processes.controllers import ProcessesInfo, list_ns_processes, list_processes
from paas_wl.bk_app.processes.entities import Instance, Process
from paas_wl.bk_app.processes.readers import (
    ProcessAPIAdapter,
    instance_kmodel,
    ns_instance_kmodel,
    ns_process_kmodel,
    process_kmodel,
)
from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.infras.resources.kube_res.base import WatchEvent
from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)
_EVENT_TYPE = WatchEvent[Union[Process, Instance]]


class ProcInstByEnvListWatcher:
    """ListWatcher for Process(Deployment) & Instance(Pod) of all modules in given environment"""

    def __init__(self, application, environment: str):
        self.application = application
        self.environment = environment
        self.module_envs = application.envs.filter(environment=environment)

    @cached_property
    def cluster_name(self):
        cluster_name = None
        module_cluster_names = {}
        for env in self.module_envs:
            cluster_name = module_cluster_names[env.module_id] = EnvClusterService(env).get_cluster_name()
        if len(set(module_cluster_names.values())) != 1:
            # TODO: 讨论解决方案, 如何解决不同集群/命名空间有不同的 rv 的问题
            raise RuntimeError("当前应用不支持 list-watch 进程信息")
        return cluster_name

    @cached_property
    def namespace(self):
        namespace = None
        module_namespaces = {}
        for env in self.module_envs:  # type: ModuleEnvironment
            namespace = module_namespaces[env.module_id] = env.wl_app.namespace
        if len(set(module_namespaces.values())) != 1:
            # TODO: 讨论解决方案, 如何解决不同集群/命名空间有不同的 rv 的问题
            raise RuntimeError("当前应用不支持 list-watch 进程信息")
        return namespace

    def list(self) -> ProcessesInfo:
        return list_ns_processes(self.cluster_name, self.namespace)

    def watch(
        self, timeout_seconds: int, rv_proc: Optional[int] = None, rv_inst: Optional[int] = None
    ) -> Generator['WatchEvent', None, None]:
        """Create a watch stream to track app's all process related changes

        :param timeout_seconds: timeout seconds for generated event stream, recommended value: less than 120 seconds
        :param rv_proc: if given, only events with greater resource_version will be returned
        :param rv_inst: same as rv_proc, but for ProcInst type
        """

        event_gens: List = [
            ns_process_kmodel.watch_by_ns(
                cluster_name=self.cluster_name,
                namespace=self.namespace,
                resource_version=rv_proc,
                timeout_seconds=timeout_seconds,
            ),
            ns_instance_kmodel.watch_by_ns(
                cluster_name=self.cluster_name,
                namespace=self.namespace,
                resource_version=rv_inst,
                timeout_seconds=timeout_seconds,
                # 由于历史原因, 存量的 Pod 有可能未添加资源类型的 label, 所以不能通过 labels 过滤进程实例
                # 这导致有可能会过滤到 slug-builder, 所以需要设置 ignore_unknown_objs=True
                ignore_unknown_objs=True,
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
            yield event
        parallel_gen.close()


class ProcInstByModuleEnvListWatcher:
    """ListWatcher for Process(Deployment) & Instance(Pod) in given ModuleEnvironment"""

    def __init__(self, env: ModuleEnvironment):
        self.env = env

    @cached_property
    def wl_app(self) -> WlApp:
        return self.env.wl_app

    def list(self) -> ProcessesInfo:
        """Build a structured data including processes and instances

        :return: A dict with "processes" and "instances"
        """
        # namespace scoped reader 需要新增的 labels 才能使用, 否则会查询不到进程(需要重新部署才会有新的 labels)
        # 因此 ProcInstByModuleEnvListWatcher 仍然使用 wl_app scoped reader 查询进程信息
        return list_processes(self.env)

    def watch(
        self, timeout_seconds: int, rv_proc: Optional[int] = None, rv_inst: Optional[int] = None
    ) -> Generator['WatchEvent', None, None]:
        """Create a watch stream to track app's all process related changes

        :param timeout_seconds: timeout seconds for generated event stream, recommended value: less than 120 seconds
        :param rv_proc: if given, only events with greater resource_version will be returned
        :param rv_inst: same as rv_proc, but for ProcInst type
        """
        event_gens: List = [
            process_kmodel.watch_by_app(
                app=self.wl_app,
                labels=ProcessAPIAdapter.app_selector(self.wl_app),
                resource_version=rv_proc,
                timeout_seconds=timeout_seconds,
            ),
            instance_kmodel.watch_by_app(
                app=self.wl_app,
                labels=ProcessAPIAdapter.app_selector(self.wl_app),
                resource_version=rv_inst,
                timeout_seconds=timeout_seconds,
                # 由于历史原因, 存量的 Pod 有可能未添加资源类型的 label, 所以不能通过 labels 过滤进程实例
                # 这导致有可能会过滤到 slug-builder, 所以需要设置 ignore_unknown_objs=True
                ignore_unknown_objs=True,
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
            yield event
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
                if value.type == 'ERROR':
                    logger.warning('Watch resource error: %s', value.error_message)
                self.queue.put(value)
        except Exception as e:
            logger.exception('Error while consuming generator: %s', str(e))
        finally:
            # Always close connection in every thread to avoid leaking of database connections
            logger.debug("generator stopped")
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
