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
from typing import TYPE_CHECKING, Optional

from django.core.exceptions import ObjectDoesNotExist

from paasng.platform.sourcectl.controllers.bk_svn import SvnRepoController

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module


logger = logging.getLogger(__name__)


class BareSvnRepoController(SvnRepoController):
    @classmethod
    def init_by_module(cls, module: "Module", operator: Optional[str] = None):
        repo_obj = module.get_source_obj()
        repo_url = repo_obj.get_repo_url()

        if not repo_url:
            raise ValueError("Require repo_url to init GeneralGitRepoController")

        from paasng.platform.sourcectl.models import RepoBasicAuthHolder

        try:
            holder = RepoBasicAuthHolder.objects.get_by_repo(module, repo_obj)
        except ObjectDoesNotExist:
            # 后续流程直接以 403 展现
            logger.warning("repo<%s> has no basic auth, maybe missing", repo_obj.get_identity())
            return cls(repo_url=repo_url, repo_admin_credentials=dict(username="", password=""))  # type: ignore

        return cls(  # type: ignore
            repo_url=repo_url,
            repo_admin_credentials={
                "username": holder.basic_auth.username,
                "password": holder.basic_auth.password,
            },
        )

    @classmethod
    def init_by_server_config(cls, source_type: str, repo_url: str):
        """Return a RepoController object from given source_type

        :param source_type: Code repository type, such as github
        :param repo_url: repository url
        """
        raise NotImplementedError
