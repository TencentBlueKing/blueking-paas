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
"""Process events related functions"""
import logging
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Iterator, List, Tuple

from paasng.engine.processes.models import PlainInstance, PlainProcess
from paasng.engine.processes.utils import diff_list

logger = logging.getLogger(__name__)


@dataclass
class ProcessBaseEvent:
    type: IntEnum
    invoker: Any


class ProcessEventType(IntEnum):
    CREATED = 1
    REMOVED = 2
    UPDATED_COMMAND = 3
    UPDATED_REPLICAS = 3


@dataclass
class ProcessEvent(ProcessBaseEvent):
    type: ProcessEventType
    invoker: PlainProcess
    message: str


class ProcInstEventType(IntEnum):
    CREATED = 1
    REMOVED = 2
    UPDATED_BECOME_READY = 3
    UPDATED_BECOME_NOT_READY = 4
    UPDATED_RESTARTED = 5


@dataclass
class ProcInstEvent(ProcessBaseEvent):
    type: ProcInstEventType
    process: PlainProcess
    invoker: PlainInstance
    message: str


class ProcEventsProducer:
    """Produces events according to processes states"""

    TYPE_EVENT_MAP: Dict[str, Tuple[ProcessEventType, ProcInstEventType, str]] = {
        'created': (ProcessEventType.CREATED, ProcInstEventType.CREATED, '{type} found'),
        'removed': (ProcessEventType.REMOVED, ProcInstEventType.REMOVED, '{type} removed'),
    }

    def __init__(self, procs_old: List[PlainProcess], procs_new: List[PlainProcess]):
        self.procs_old = procs_old
        self.procs_new = procs_new

    def produce(self) -> Iterator[ProcessBaseEvent]:
        """Yields events which represents the process list's state changes"""
        procs_old_names = [inst.name for inst in self.procs_old]
        procs_new_names = [inst.name for inst in self.procs_new]
        procs_added, procs_removed, procs_both = diff_list(procs_old_names, procs_new_names)

        # Process added processes
        for proc_name in procs_added:
            process = self._get_proc_by_name(self.procs_new, proc_name)
            yield from self.proc_process_pure(process, 'created')

        # Process removed processes
        for proc_name in procs_removed:
            process = self._get_proc_by_name(self.procs_old, proc_name)
            yield from self.proc_process_pure(process, 'removed')

        # Process both exists processes
        for proc_name in procs_both:
            proc_old = self._get_proc_by_name(self.procs_old, proc_name)
            proc_new = self._get_proc_by_name(self.procs_new, proc_name)
            yield from self.proc_process_updated(proc_old, proc_new)

    def proc_process_pure(self, process: PlainProcess, type: str) -> Iterator[ProcessBaseEvent]:
        """Generates events by added/removed process"""
        if type not in self.TYPE_EVENT_MAP:
            raise ValueError('Invalid type')

        proc_event_type, inst_event_type, msg_tmpl = self.TYPE_EVENT_MAP[type]
        yield ProcessEvent(type=proc_event_type, invoker=process, message=msg_tmpl.format(type='process'))
        for instance in process.instances:
            yield ProcInstEvent(
                type=inst_event_type, invoker=instance, process=process, message=msg_tmpl.format(type='instance')
            )

    def proc_process_updated(self, proc_old: PlainProcess, proc_new: PlainProcess) -> Iterator[ProcessBaseEvent]:
        """Generates events by both exists process"""
        if proc_new.command != proc_old.command:
            yield ProcessEvent(
                type=ProcessEventType.UPDATED_COMMAND, invoker=proc_new, message='process command changed'
            )

        if proc_new.replicas != proc_old.replicas:
            yield ProcessEvent(
                type=ProcessEventType.UPDATED_REPLICAS, invoker=proc_new, message='process desired replicas changed'
            )

        # Detect instances changes
        yield from ProcInstanceEventsProducer(proc_new, proc_old.instances, proc_new.instances).produce()

    def _get_proc_by_name(self, processes: List[PlainProcess], name: str) -> PlainProcess:
        """Find an Process by name"""
        try:
            return next(process for process in processes if process.name == name)
        except StopIteration:
            raise KeyError(name)


class ProcInstanceEventsProducer:
    """Produces events according to process's instances states"""

    def __init__(self, process: PlainProcess, insts_old: List[PlainInstance], insts_new: List[PlainInstance]):
        self.process = process
        self.insts_old = insts_old
        self.insts_new = insts_new

    def produce(self) -> Iterator[ProcInstEvent]:
        insts_old_names = [inst.name for inst in self.insts_old]
        insts_new_names = [inst.name for inst in self.insts_new]
        insts_added, insts_removed, insts_both = diff_list(insts_old_names, insts_new_names)

        # Process added instances
        for name in insts_added:
            instance = self._get_inst_by_name(self.insts_new, name)
            yield ProcInstEvent(
                type=ProcInstEventType.CREATED, invoker=instance, process=self.process, message='instance created'
            )

        # Process removed instances
        for name in insts_removed:
            instance = self._get_inst_by_name(self.insts_old, name)
            yield ProcInstEvent(
                type=ProcInstEventType.REMOVED, invoker=instance, process=self.process, message='instance removed'
            )

        # Process updated instances
        for name in insts_both:
            inst_old = self._get_inst_by_name(self.insts_old, name)
            inst_new = self._get_inst_by_name(self.insts_new, name)
            yield from self.process_updated(inst_old, inst_new)

    def process_updated(self, inst_old: PlainInstance, inst_new: PlainInstance) -> Iterator[ProcInstEvent]:
        """Generates events by both exists objects"""
        if inst_new.restart_count > inst_old.restart_count:
            yield ProcInstEvent(
                type=ProcInstEventType.UPDATED_RESTARTED,
                invoker=inst_new,
                process=self.process,
                message='instance restarted',
            )

        if inst_new.ready and not inst_old.ready:
            yield ProcInstEvent(
                type=ProcInstEventType.UPDATED_BECOME_READY,
                invoker=inst_new,
                process=self.process,
                message='instance became ready',
            )

        if inst_old.ready and not inst_new.ready:
            yield ProcInstEvent(
                type=ProcInstEventType.UPDATED_BECOME_NOT_READY,
                invoker=inst_new,
                process=self.process,
                message='instance became not ready',
            )

    def _get_inst_by_name(self, insts: List[PlainInstance], name: str) -> PlainInstance:
        """Find an instance by name"""
        try:
            return next(inst for inst in insts if inst.name == name)
        except StopIteration:
            raise KeyError(name)
