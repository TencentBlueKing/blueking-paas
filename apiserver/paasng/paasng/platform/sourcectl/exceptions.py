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

"""Exceptions for sourcectl package"""

from typing import TYPE_CHECKING, Optional

from django.utils.translation import gettext as _

if TYPE_CHECKING:
    from .models import GitProject  # noqa: F401


class RemoteResourceNotFoundError(Exception):
    """A base common exception for remote resource not found errors."""


class ReadFileNotFoundError(Exception):
    """File not found when reading file from remote repository"""


class ReadLinkFileOutsideDirectoryError(Exception):
    """When trying to read a link file that link to outside the directory of the repository."""


class BasePackageError(Exception):
    """The base error class for package clients."""


class PackageInvalidFileFormatError(BasePackageError):
    """The package file is not in a valid format, it might be corrupt."""


class GitLabCommonError(Exception):
    pass


class AccessTokenError(Exception):
    """access token 校验失败"""


class AccessTokenHolderError(Exception):
    """token holder 异常（如：未提供）"""


class RequestError(Exception):
    """请求异常"""


class RequestTimeOutError(RequestError):
    """请求超时"""


class AccessTokenMissingError(AccessTokenError):
    """缺少 access token"""


class ExceptionWithGitProject(Exception):
    def __init__(self, *args, project: Optional["GitProject"] = None):
        self.project = project
        super().__init__(*args)

    @property
    def fullname(self):
        return getattr(self.project, "path_with_namespace", None)

    def __str__(self):
        return _("访问 Git<{fullname}> 项目异常").format(fullname=self.fullname)


class UserNotBindedToSourceProviderError(ExceptionWithGitProject):
    """用户未提供服务源码仓库的凭据"""


class AccessTokenForbidden(ExceptionWithGitProject):
    """Access token 无权限"""


class AccessTokenRefreshError(AccessTokenError):
    pass


class ExceptionWithMessage(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class GetProcfileError(ExceptionWithMessage):
    """When no valid Procfile can be found in application directory"""


class GetProcfileFormatError(GetProcfileError):
    """The Procfile exists but the content format is incorrect"""


class GetAppYamlError(ExceptionWithMessage):
    """When no valid app_desc.yaml can be found in application directory"""


class GetAppYamlFormatError(GetAppYamlError):
    """The app_desc.yaml exists but the content format is incorrect"""


class GetDockerIgnoreError(ExceptionWithMessage):
    """When .dockerignore can not be found in application directory"""


class GitAPIError(ExceptionWithMessage):
    """When git api return error"""


class RepoNameConflict(ExceptionWithMessage):
    """仓库名称冲突, 同名仓库已存在"""


class GitLabBranchNameBugError(Exception):
    """existing bug in gitlab
    https://gitlab.com/gitlab-org/gitlab-ce/issues/42231
    """


class PackageAlreadyExists(Exception):
    """源码包已存在"""


class GitBranchNotFound(Exception):
    """git 仓库找不到对应分支"""


class UnsupportedGitRepoEncode(Exception):
    """当前编码格式不受支持"""


class DownloadGitZipBallError(Exception):
    """下载源码包失败"""


class CallGitApiFailed(Exception):
    """调用 Git API 失败"""


class BasicAuthError(Exception):
    """用户名/密码错误"""


class OauthAuthorizationRequired(Exception):
    """需要进行 Oauth 授权"""

    def __init__(self, authorization_url: str, auth_docs: str = ""):
        super().__init__(authorization_url, auth_docs)
        self.authorization_url = authorization_url
        self.auth_docs = auth_docs
