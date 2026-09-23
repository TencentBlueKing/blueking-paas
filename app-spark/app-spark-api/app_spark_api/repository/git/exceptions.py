# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""Git 仓库生命周期相关的失败。"""


class GitBackendError(Exception):
    """Git 持久化（repo-server）或仓库生命周期出了问题。"""


class RepoServerConfigurationError(GitBackendError, ValueError):
    """``REPO_SERVER`` 缺失或无法使用。进程不能带着这份配置启动。"""


class GitRepositoryNotReadyError(GitBackendError):
    """仓库还不能给 Agent 用：未建、仍在 pending，或上次建仓失败。

    重试同一请求不会自己变好，要先走补建入口。
    """
