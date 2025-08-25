# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import datetime
from textwrap import dedent
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


def default_created():
    dt = datetime.datetime.utcnow()
    return dt.replace(microsecond=0, tzinfo=datetime.timezone.utc)


class HealthConfig(BaseModel):
    Test: List[str] = Field(
        ...,
        description=dedent(
            """
        Test is the test to perform to check that the container is healthy.
        An empty slice means to inherit the default.
        The options are:
        {} : inherit healthcheck
        {"NONE"} : disable healthcheck
        {"CMD", args...} : exec arguments directly
        {"CMD-SHELL", command} : run command with system's default shell
    """
        ),
    )
    Interval: int = Field(..., description="the time to wait between checks.")
    Timeout: int = Field(..., description="the time to wait before considering the check to have hung.")
    StartPeriod: int = Field(
        ...,
        description="the period for the container to initialize before the retries starts to count down.",
    )
    Retries: int = Field(
        ...,
        description="the number of consecutive failures needed to consider a container as unhealthy.",
    )


class ContainerConfig(BaseModel):
    """ContainerConfig contains the configuration data when running a container using the image
    spec: https://github.com/opencontainers/image-spec/blob/main/config.md
    """

    User: str = Field(
        "",
        description="User that will run the command(s) inside the container, also support user:group",
    )
    Memory: Optional[int] = Field(default=None, description="Memory limit (in bytes)")
    MemorySwap: Optional[int] = Field(
        default=None,
        description=" Total memory usage (memory + swap); set `-1` to enable unlimited swap",
    )
    CpuShares: Optional[int] = Field(default=None, description="CPU shares (relative weight vs. other containers)")
    ExposedPorts: Optional[Dict[str, Dict]] = Field(None, description="List of exposed ports")
    Env: Optional[List[str]] = Field(default=None, description="List of environment variable to set in the container")
    Entrypoint: Optional[List[str]] = Field(
        None,
        description="A list of arguments to use as the command to execute when the container starts. ",
    )
    Cmd: Optional[List[str]] = Field(
        default=None,
        description="Default arguments to the entrypoint of the container.",
    )
    Volumes: Optional[Dict] = Field(default=None, description="List of volumes (mounts) used for the container.")
    WorkingDir: Optional[str] = Field(
        default=None,
        description="Current directory (PWD) in the command will be launched",
    )
    Labels: Optional[Dict[str, str]] = Field(default=None, description="List of labels set to this container")
    StopSignal: Optional[str] = Field(
        default=None,
        description="The signal that will be sent to the container to exit.",
    )
    Healthcheck: Optional[HealthConfig] = Field(
        default=None,
        description="Healthcheck describes how to check the container is healthy",
    )


class RootFS(BaseModel):
    diff_ids: List[str] = Field(..., description="diff id is the digest of uncompressed tarball")
    type: str = "layers"


class History(BaseModel):
    created: Optional[datetime.datetime] = Field(default_factory=default_created)
    author: Optional[str] = None
    created_by: Optional[str] = None
    comment: Optional[str] = None
    empty_layer: Optional[bool] = False


class ImageJSON(BaseModel):
    created: datetime.datetime
    author: str = "anonymous"
    architecture: str
    os: str
    variant: Optional[str] = Field(default=None, description="The variant of the specified CPU architecture.")
    config: ContainerConfig
    rootfs: RootFS
    history: List[History]
