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


class BKAppOauthError(Exception):
    def __init__(self, error_message="", response_code=None, raw_response=None):
        super().__init__(self, error_message)
        # Http status code
        self.response_code = response_code
        # Full http response
        self.raw_response = raw_response
        # Parsed error message from gitlab
        self.error_message = error_message

    def __str__(self):
        if self.response_code is not None:
            return "{0}: {1}".format(self.response_code, self.error_message)
        else:
            return "{0}".format(self.error_message)


class BKAppOauthRequestError(BKAppOauthError):
    """调用 BKApp Oauth 接口异常"""


class BKAppOauthResponseError(BKAppOauthError):
    """BKApp Oauth 接口返回异常"""
