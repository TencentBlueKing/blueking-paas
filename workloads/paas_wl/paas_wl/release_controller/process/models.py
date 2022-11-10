# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from typing import List, Optional

from paas_wl.workloads.processes.models import Process, Status


def condense_processes(processes: List[Process]) -> 'List[PlainProcess]':
    """Condense processes by removing unrelated fields to save space."""
    plain = []
    for p in processes:
        plain.append(
            PlainProcess(
                name=p.name,
                version=p.version,
                replicas=p.replicas,
                type=p.type,
                command=p.runtime.proc_command,
                status=p.status,
                instances=[
                    PlainInstance(
                        name=inst.name,
                        version=inst.version,
                        process_type=inst.process_type,
                        state=inst.state,
                        ready=inst.ready,
                        restart_count=inst.restart_count,
                    )
                    for inst in p.instances
                ],
            )
        )
    return plain


@dataclass
class PlainInstance:
    name: str
    version: int
    process_type: str
    state: str = ""
    ready: bool = True
    restart_count: int = 0

    @property
    def shorter_name(self) -> str:
        """Return a simplified name

        >>>simplify_name('default-gunicorn-deployment-59b9789f76wk82')
        '59b9789f76wk82'
        """
        return self.name.split('-')[-1]

    def is_ready_for(self, expected_version: int) -> bool:
        """detect if the instance if ready for the given version"""
        return self.ready and self.version == expected_version


@dataclass
class PlainProcess:
    name: str
    version: int
    replicas: int
    type: str
    command: str
    status: Optional[Status] = None
    instances: List[PlainInstance] = field(default_factory=list)

    def is_all_ready(self, expected_version: int) -> bool:
        """detect if all instances are ready"""
        if expected_version != self.version:
            return False

        return sum(inst.is_ready_for(expected_version) for inst in self.instances) == self.replicas
