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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Protocol, Type, Union

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.utils.command import get_command_name

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import Release

logger = logging.getLogger(__name__)


class Process(Protocol):
    """A protocol that represents a process object with necessary field only."""

    app: WlApp
    type: str
    version: int
    runtime: Any


class ResourceIdentifiers:
    """A class that stores the identifiers for kubernetes resources, such as name, labels."""

    def __init__(self, process: "Union[Process, MapperProcConfig]"):
        if not isinstance(process, MapperProcConfig):
            _proc_config = get_mapper_proc_config(process)
            if not _proc_config:
                raise TypeError("process argument is invalid")
        else:
            _proc_config = process

        self.proc_config: "MapperProcConfig" = _proc_config

    @property
    def name(self) -> str:
        """获取资源名"""
        raise NotImplementedError

    @property
    def labels(self) -> dict:
        """创建该资源时添加的 labels"""
        raise NotImplementedError

    @property
    def match_labels(self) -> dict:
        """用于匹配该资源时使用的 labels"""
        raise NotImplementedError

    @property
    def pod_selector(self) -> str:
        """用户匹配 pod 的选择器"""
        raise NotImplementedError

    @property
    def namespace(self):
        """对于目前所有资源，namespace 都和 process 保持一致"""
        return self.proc_config.app.namespace


class MapperPack:
    version: str

    # Set these identifier types in child classes
    pod: Type[ResourceIdentifiers] = ResourceIdentifiers
    deployment: Type[ResourceIdentifiers] = ResourceIdentifiers
    replica_set: Type[ResourceIdentifiers] = ResourceIdentifiers


@dataclass
class MapperProcConfig:
    """The config object for initializing a resource mapper."""

    app: WlApp
    # The type of the process, such as "web"
    type: str
    # The release version of the process
    version: int
    command_name: str


def get_mapper_proc_config(proc: Process) -> Optional[MapperProcConfig]:
    """Try to get the proc_config object by the given process object.

    :param proc: The input process object.
    :return: None if given object is not a valid Process.
    """
    try:
        # Try parse `Process` type from the process package
        return MapperProcConfig(
            app=proc.app,
            type=proc.type,
            version=proc.version,
            command_name=get_command_name(proc.runtime.proc_command),
        )
    except Exception:
        logger.warning("Error getting mapper_proc_config object, process: %s", proc)
        return None


def get_mapper_proc_config_from_release(release: "Release", process_type: str) -> MapperProcConfig:
    """Get the proc config object by release.

    :param release: The release object.
    :param process_type: The type of process.
    """
    version = release.version
    command_name = get_command_name(release.get_procfile()[process_type])
    return MapperProcConfig(app=release.app, type=process_type, version=version, command_name=command_name)
