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

"""发起发布时的领域错误，由 api.py 翻译成对外错误码。"""


class PublicationError(Exception):
    """Base class of failures starting a publication task."""


class PublicationTaskInProgressError(PublicationError):
    """The Project already has a publication task running."""


class PublicationVersionNotFoundError(PublicationError):
    """The version does not belong to the Project, or cannot be published."""


class PublicationAppNameInvalidError(PublicationError):
    """The application name keeps nothing once the developer center's character rules are applied."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Application name {name!r} has no character the developer center keeps")
        self.name = name


class PublicationSubmitError(PublicationError):
    """Creating the developer center application failed; the message says why."""
