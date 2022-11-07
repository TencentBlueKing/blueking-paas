# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from paas_wl.platform.applications.models import App
from paas_wl.platform.applications.models.release import Release

from .models import Process

logger = logging.getLogger(__name__)


@dataclass
class AppProcessManager:
    """
    从 App 维度操作 Process
    """

    app: 'App'

    def assemble_process(
        self, process_type: str, release: Optional['Release'] = None, extra_envs: Optional[dict] = None
    ) -> Process:
        """通过 Release 对象组装单个 Process 对象"""
        if not release:
            release = Release.objects.get_latest(self.app)

        return Process.from_release(process_type, release, extra_envs)

    def assemble_processes(
        self, release: Optional['Release'] = None, extra_envs: Optional[dict] = None
    ) -> Iterable[Process]:
        """通过 Release 对象组装 App 所有 Process 对象"""
        if not release:
            release = Release.objects.get_latest(self.app)

        for process_type in release.get_procfile().keys():
            yield self.assemble_process(process_type, release, extra_envs)
