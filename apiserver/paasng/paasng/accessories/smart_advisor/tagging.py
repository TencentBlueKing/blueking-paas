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

"""Tagging tools"""

import logging
import re
from os import PathLike
from pathlib import Path
from typing import List

from paasng.platform.engine.logs import get_all_logs
from paasng.platform.engine.models.deployment import Deployment

from .constants import DeployFailurePatternType
from .models import DeployFailurePattern
from .tags import Tag, force_tag, get_dynamic_tag

logger = logging.getLogger(__name__)


def dig_tags_local_repo(local_path: str | PathLike):
    """Dig a local repo to find proper tags for this module"""
    p = Path(local_path)
    if not p.exists():
        return []

    tags = []
    # Python detection
    req_file = p / "requirements.txt"

    # Because we will read the requirements.txt file later, we should ensure it exists
    # and is not a symlink because the file was created by the user.
    if req_file.exists() and not req_file.is_symlink():
        tags.append(force_tag("app-pl:python"))
        # Set `errors="ignore"` to ignore non-ascii characters when the file is using a
        # different encoding other than utf-8.
        requirements_txt = req_file.read_text(encoding="utf-8", errors="ignore")
        for pkg_name in ("celery", "django", "gunicorn", "blueapps"):
            if py_module_in_requirements(pkg_name, requirements_txt):
                tags.append(force_tag("app-sdk:{}".format(pkg_name)))

    # golang and other language detection is still naive, need improve
    for fname in p.iterdir():
        if fname.name.endswith(".go"):
            tags.append(force_tag("app-pl:go"))
            break
        if fname.name.endswith(".php"):
            tags.append(force_tag("app-pl:php"))
            break

    if (p / "package.json").exists() and (p / "index.js").exists():
        tags.append(force_tag("app-pl:nodejs"))
    return tags


def py_module_in_requirements(name, requirements):
    """Check if a module was defined in python requirements"""
    for raw_line in requirements.split("\n"):
        line = raw_line.strip().lower()
        if line.startswith("#"):
            continue

        obj = re.search(r"^[\w.-]+", line)
        if not obj:
            continue
        if obj.group() == name:
            return True
    return False


def get_deployment_tags(deployment: Deployment) -> List[Tag]:
    """Get tags for a deployment object"""
    patterns = DeployFailurePattern.objects.filter(type=DeployFailurePatternType.REGULAR_EXPRESSION)
    tag_strs = []

    # Find deployment failure tags by comparing logs with existed patterns
    logs = get_all_logs(deployment)
    for pattern in patterns:
        if re.search(pattern.value, logs, re.IGNORECASE):
            logger.debug("Deployment failure pattern match found: %s", pattern.value)
            tag_strs.append(pattern.tag_str)

    return [get_dynamic_tag(tag_str) for tag_str in tag_strs]
