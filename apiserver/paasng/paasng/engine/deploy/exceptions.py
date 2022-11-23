# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""


class DeployShouldAbortError(Exception):
    """Raise this exception when a deploy procedure should be aborted.
    Using this exception means that the error reason can be displayed to users directly.

    :param reason: The user-friendly reason to be displayed on screen and recorded in database
    :param exc: Raw exception object
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(self.reason)

    def __str__(self):
        return self.reason
