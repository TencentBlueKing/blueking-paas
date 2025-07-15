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
from pathlib import Path
from typing import TYPE_CHECKING

from paasng.platform.declarative.handlers import get_deploy_desc_by_module
from paasng.platform.engine.utils.patcher import patch_source_dir_procfile
from paasng.platform.engine.utils.source import validate_source_dir_str
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.sourcectl.models import SPStat
from paasng.platform.sourcectl.package.client import BinaryTarClient
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


logger = logging.getLogger(__name__)


def patch_smart_tarball(tarball_path: Path, dest_dir: Path, module: "Module", stat: SPStat) -> Path:
    """Patch a s-mart source package to add Procfile, return a new package path.

    :param tarball_path: Path to the origin source package tarball.
    :param dest_dir: Directory to save the patched tarball.
    :param module: The module object.
    :param stat: The source package stat object.
    :return: Path to the patched tarball.
    """
    dest = Path(dest_dir) / stat.name

    with generate_temp_dir() as temp_dir:
        BinaryTarClient(tarball_path).export(str(temp_dir.absolute()))

        root_dir = temp_dir
        root_rel_dir = root_dir / stat.relative_path
        deploy_desc = get_deploy_desc_by_module(stat.meta_info, module.name)

        # Get source directory
        # TODO: 让 RepositoryInstance.get_source_dir 屏蔽 source_origin 这个差异
        # 由于 Package 的 source_dir 是由与 VersionInfo 绑定的. 需要调整 API.
        if ModuleSpecs(module).deploy_via_package:
            source_dir_str = deploy_desc.source_dir
        else:
            source_dir_str = module.get_source_obj().get_source_dir()
        source_dir = validate_source_dir_str(root_rel_dir, source_dir_str)

        if reason := patch_source_dir_procfile(source_dir=source_dir, procfile=deploy_desc.get_procfile()):
            logger.warning("skip patching for adding Procfile: %s", reason)

        # Recompress the directory to a new tarball
        compress_directory(root_dir, dest)
        return dest
