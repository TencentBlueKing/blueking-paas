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
import os
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from paasng.accessories.dev_sandbox.client import DevSandboxApiClient
from paasng.accessories.dev_sandbox.exceptions import CannotCommitToRepository
from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.modules.models import Module
from paasng.platform.sourcectl.constants import FileChangeType, VersionType
from paasng.platform.sourcectl.exceptions import CallGitApiFailed
from paasng.platform.sourcectl.models import ChangedFile, CommitInfo
from paasng.platform.sourcectl.repo_controller import get_repo_controller

logger = logging.getLogger(__name__)


class DevSandboxCodeCommit:
    """开发沙箱代码提交"""

    def __init__(self, module: Module, operator: str):
        self.module = module
        self.operator = operator

        self.dev_sandbox = DevSandbox.objects.get(owner=operator, module=module)
        self.api_client = DevSandboxApiClient(module=module, dev_sandbox=self.dev_sandbox, operator=operator)

    def commit(self, message: str) -> str:
        """提交代码

        :param message: 提交信息
        :return: 代码仓库 Url
        '"""
        # 1. 调用 devserver api 获取代码差异信息
        diffs = self.api_client.fetch_diffs()
        # 2. 构建提交信息（CommitInfo）
        commit_info = self._build_commit_info(diffs, message)
        # 3. 调用代码库 API 提交代码
        repo_url = self._commit_to_repository(commit_info)
        # 4. 在沙箱中也进行一次 commit，否则无法重复提交
        self.api_client.commit(message)

        return repo_url

    def _build_commit_info(self, diffs: List[Dict], commit_msg: str) -> CommitInfo:
        """根据变更的文件构建提交信息

        :param diffs: 变更的文件列表，格式如：
            [
                {"path": "webfe/app.js", "action": "added", "content": "..."},
                {"path": "api/main.py", "action": "modified", "content": "..."},
                {"path": "backend/cmd/main.go", "action": "deleted", "content": "..."},
            ]
        :param commit_msg: 提交信息
        :return: 提交详细信息
        """
        # 代码部署目录
        source_dir = self.module.get_source_obj().get_source_dir()

        commit_info = CommitInfo(branch=self.dev_sandbox.version_info.version_name, message=commit_msg)
        mapping = {
            FileChangeType.ADDED: commit_info.add_files,
            FileChangeType.MODIFIED: commit_info.edit_files,
            FileChangeType.DELETED: commit_info.delete_files,
        }
        for item in diffs:
            path = os.path.join(source_dir, item["path"]) if source_dir else item["path"]
            mapping[item["action"]].append(ChangedFile(path, item["content"]))

        return commit_info

    def _commit_to_repository(self, commit_info: CommitInfo) -> str:
        """提交代码到代码库

        :return: 代码库访问地址
        """
        repo_ctrl = get_repo_controller(self.module, self.operator)
        try:
            repo_ctrl.commit_files(commit_info)
        except CallGitApiFailed as e:
            logger.exception("failed to commit code to repository")
            raise CannotCommitToRepository(_("提交代码到代码库失败")) from e

        version_info = self.dev_sandbox.version_info
        repo_url = repo_ctrl.build_url(version_info)

        if version_info.version_type != VersionType.BRANCH:
            return repo_url

        # 如果版本类型是分支，访问地址可以更具体一些
        return f"{repo_url.removesuffix('.git')}/tree/{version_info.version_name}"
