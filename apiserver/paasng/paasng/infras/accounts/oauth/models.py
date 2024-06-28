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

import logging
import re
from dataclasses import dataclass
from typing import Protocol

from .constants import ScopeType

logger = logging.getLogger(__name__)


class Project(Protocol):
    """A simple type that provides VCS project name info."""

    type: str
    # The name of the project
    name: str

    @property
    def path_with_namespace(self) -> str:
        """The full path with the namespace as prefix"""
        ...


@dataclass
class Scope:
    type: ScopeType
    item: str

    @classmethod
    def parse_from_str(cls, scope_str) -> "Scope":
        """
        example:
            ["user:user"]
            ["project:bkpaas/Skynet"]
            ["group:v3-test-group"]
        """
        # repo for github, user_info, projects for gitee
        if scope_str in ["api", "repo", "user_info", "projects", ""]:
            return cls(type=ScopeType.USER, item="user")

        try:
            parse_result = re.match(r"(?P<type>\w+):(?P<item>[a-zA-Z0-9_/-]+)", scope_str).groupdict()  # type: ignore
            return cls(type=ScopeType(parse_result["type"]), item=parse_result["item"])
        except (KeyError, ValueError):
            logger.warning(f"scope<{scope_str}> does not match regex")
            raise

    def cover_project(self, project: Project) -> bool:
        if self.type == ScopeType.USER:
            return True

        if self.type == ScopeType.GROUP:
            return f"{self.item}/{project.name}" == project.path_with_namespace

        if self.type == ScopeType.PROJECT:
            return self.item == project.path_with_namespace
        return False
