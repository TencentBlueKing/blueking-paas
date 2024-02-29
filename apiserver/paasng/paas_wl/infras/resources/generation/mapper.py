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
from typing import Any, Optional, Protocol, Type, Union

from paas_wl.bk_app.applications.models import Release, WlApp
from paas_wl.utils.command import get_command_name

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
            _proc_config = _to_mapper_proc_config(process)
            if not _proc_config:
                raise TypeError("process argument is invalid")
        else:
            _proc_config = process

        self.proc_config: "MapperProcConfig" = _proc_config

    @property
    def pod_name(self) -> str:
        """The name of pod resource."""
        raise NotImplementedError

    @property
    def deployment_name(self) -> str:
        """The name of deployment resource."""
        raise NotImplementedError

    @property
    def match_labels(self) -> dict:
        """The labels for matching the pods."""
        raise NotImplementedError

    @property
    def pod_selector(self) -> str:
        """The labels for selecting the pods, used by services."""
        raise NotImplementedError

    @property
    def labels(self) -> dict:
        """The labels for creating workloads."""
        raise NotImplementedError


class MapperPack:
    version: str

    # Set the identifier type in child classes
    proc_resources: Type[ResourceIdentifiers] = ResourceIdentifiers


@dataclass
class MapperProcConfig:
    """The config object for initializing a resource mapper."""

    app: WlApp
    # The type of the process, such as "web"
    type: str
    # The release version of the process
    version: int
    command_name: str


def get_mapper_proc_config(release: "Release", process_type: str) -> MapperProcConfig:
    """Get the proc config object by release.

    :param release: The release object.
    :param process_type: The type of process.
    """
    version = release.version
    command_name = get_command_name(release.get_procfile()[process_type])
    return MapperProcConfig(app=release.app, type=process_type, version=version, command_name=command_name)


def get_mapper_proc_config_latest(app: "WlApp", process_type: str, use_default: bool = True) -> MapperProcConfig:
    """Get the proc config object, use the latest release object by default.

    :param app: The app object.
    :param process_type: The type of process.
    :param use_default: Whether to use the default config if no release object found.
    :raise: ValueError when no release object found and `use_default` is False.
    """
    # Get the command name by reading the latest successful release
    try:
        release = Release.objects.get_latest(app)
        version = release.version
        command_name = get_command_name(release.get_procfile()[process_type])
    except (Release.DoesNotExist, KeyError):
        logger.warning("Unable to get the deployment name of %s, app: %s", process_type, app)
        if use_default:
            return MapperProcConfig(app=app, type=process_type, version=1, command_name="")
        raise ValueError(f"invalid proc type: {process_type}")
    return MapperProcConfig(app=app, type=process_type, version=version, command_name=command_name)


def _to_mapper_proc_config(proc: Process) -> Optional[MapperProcConfig]:
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
