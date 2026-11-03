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

"""发布流程对版本和打包的依赖。

还没有面向用户的版本列表，版本暂时就是会话检查点的 tag（形如 app-spark/checkpoint/<run_id>）：
每轮对话结束 Agent 推送一个不可移动的 tag，钉住那一轮的提交。打包用 repository.git.source_packages，
把 tag 对应的提交打成源码包存进制品库，再签一个带有效期的下载链接给开发者中心。
"""

from typing import TYPE_CHECKING

import attrs
from django.core.exceptions import ImproperlyConfigured

from app_spark_api.agent.conversations.state_models import ConversationCheckpoint
from app_spark_api.infras.forgejo.exceptions import ForgejoError
from app_spark_api.repository.git.exceptions import (
    GitRepositoryNotReadyError,
    SourcePackageError,
    SourceRefNotFoundError,
)
from app_spark_api.repository.git.models import ProjectGitRepository
from app_spark_api.repository.git.source_packages import RepoPackager, agenerate_source_package_url

if TYPE_CHECKING:
    from app_spark_api.core.projects.models import Project

# 所有项目共用 buildpack：开发者中心的 Python 构建工具已支持 heroku-24、Python 3.14 与 uv。
BUILD_METHOD = "buildpack"
# 开发者中心在上传那一步就按链接把包下载走，不需要长期有效；有效期越短，链接泄露的影响越小。
PACKAGE_URL_EXPIRES_IN = 30 * 60
# 版本号的长度上限。上传接口允许 128，但部署记录（Deployment.source_version_name）只存得下 64。
_MAX_ARTIFACT_VERSION_LENGTH = 64


class SourcePackagingError(Exception):
    """Packing a version failed; the message is shown to the owner as the reason."""


@attrs.frozen
class PackagedSource:
    """A version packed into a source package the developer center can download.

    :param version: 上传源码包和部署时都用它作为开发者中心的源码包版本号。
    :param package_url: 带有效期的下载链接。
    """

    version: str
    package_url: str


async def aversion_exists(project: Project, version_id: str) -> bool:
    """Return whether the version belongs to the project and can be published."""
    # 只认本项目会话留下的检查点：tag 名字可以猜，但别的项目的检查点不能拿来发布。
    return await ConversationCheckpoint.objects.filter(conversation__project=project, tag=version_id).aexists()


async def apackage_version(project: Project, version_id: str) -> PackagedSource:
    """Pack a version and return where the developer center can download it.

    :raises SourcePackagingError: 打包或上传制品失败。
    """
    repo = await ProjectGitRepository.objects.filter(project=project).afirst()
    if repo is None:
        raise SourcePackagingError("项目还没有代码仓库，暂时无法发布")

    # 同一提交只打包一次，重复调用复用已有制品；链接每次都重新签，因为它会过期而制品不会。
    try:
        package = await RepoPackager(repo).aupload(tag=version_id)
        package_url = await agenerate_source_package_url(package, expires_in=PACKAGE_URL_EXPIRES_IN)
    except GitRepositoryNotReadyError as exc:
        raise SourcePackagingError("项目的代码仓库还没有就绪，暂时无法发布") from exc
    except SourceRefNotFoundError as exc:
        raise SourcePackagingError(f"代码仓库里找不到版本「{version_id}」") from exc
    except (SourcePackageError, ForgejoError, ImproperlyConfigured) as exc:
        raise SourcePackagingError("打包源码失败，请稍后重试") from exc

    # tag 带斜杠（app-spark/checkpoint/<run_id>），版本号会出现在部署记录里，只留最后一段。
    name = version_id.rsplit("/", 1)[-1]
    version = f"{name}-{package.commit_sha[:7]}"[-_MAX_ARTIFACT_VERSION_LENGTH:]
    return PackagedSource(version=version, package_url=package_url)
