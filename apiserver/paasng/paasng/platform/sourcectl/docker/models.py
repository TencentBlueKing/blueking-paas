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

from typing import Dict

from paasng.platform.applications.models import Application
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.models import DockerRepository, RepoBasicAuthHolder

REPO_TYPE = "docker"


def get_or_create_repo_obj(
    application: Application, repo_type: str, repo_url: str, source_dir: str
) -> DockerRepository:
    """Get or create a repository object by given url and source_dir."""
    repo_kwargs = {
        "region": application.region,
        "server_name": repo_type,
        "repo_url": repo_url,
        "source_dir": source_dir,
    }
    # Not using `get_or_create` because it might return more than 1 results
    repo_objs = DockerRepository.objects.filter(**repo_kwargs)[:1]
    if repo_objs:
        return repo_objs[0]
    return DockerRepository.objects.create(owner=application.owner, tenant_id=application.tenant_id, **repo_kwargs)


def init_image_repo(module: Module, repo_url: str, source_dir: str, repo_auth_info: Dict):
    """Init a container image based module's repo related info

    TODO: Change names started with "repo_" to another name in order to distinguish from other VCS-based concepts.
    """
    if not repo_url:
        raise ValueError('must provide "repo_url"')

    repo_obj = get_or_create_repo_obj(module.application, REPO_TYPE, repo_url, source_dir)
    module.source_type = REPO_TYPE
    module.source_repo_id = repo_obj.id
    module.save(update_fields=["source_type", "source_repo_id"])

    # Create related basic auth credentials
    RepoBasicAuthHolder.objects.update_or_create(
        repo_id=repo_obj.get_identity(),
        repo_type=repo_obj.get_source_type(),
        module=module,
        defaults={
            "username": repo_auth_info.get("username", ""),
            "password": repo_auth_info.get("password", ""),
            "tenant_id": module.tenant_id,
        },
    )
