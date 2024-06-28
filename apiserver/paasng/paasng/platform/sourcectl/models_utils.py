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

from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models.module import Module, set_source_obj_finder_func
from paasng.platform.modules.specs import ModuleSpecs
from paasng.platform.sourcectl.models import (
    DockerRepository,
    GitRepository,
    RepositoryInstance,
    SourcePackageRepository,
    SvnRepository,
)
from paasng.platform.sourcectl.source_types import get_sourcectl_names

logger = logging.getLogger(__name__)


def find_by_module(module: Module) -> RepositoryInstance:
    """Find the repository inst by the given module"""
    names = get_sourcectl_names()

    if names.validate_svn(module.source_type):
        return SvnRepository.objects.get(pk=module.source_repo_id)
    elif names.validate_git(module.source_type):
        return GitRepository.objects.get(pk=module.source_repo_id)
    elif module.get_source_origin() in [SourceOrigin.IMAGE_REGISTRY]:
        return DockerRepository.objects.get(pk=module.source_repo_id)
    elif ModuleSpecs(module).deploy_via_package:
        return SourcePackageRepository(module)

    # NOTE: 2020.08.19. 调整中, 目前这里不能保证必然有返回值
    logger.warning("Can't get source obj from %s", module)
    return None  # type: ignore


# Set the finder function
set_source_obj_finder_func(find_by_module)
