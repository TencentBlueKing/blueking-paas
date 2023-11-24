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


class RequestMetricBackendError(Exception):
    """got exception during requesting to prometheus"""

    def __init__(self, resp):
        self.response = resp
        self.status_code = resp.status_code
        try:
            self.json_response = resp.json()
        except Exception:
            self.json_response = {}
        self.error_code = self.get_error_code()
        self.error_message = self.get_error_message()

    def get_error_code(self):
        return self.json_response.get("code", "UNKNOWN")

    def get_error_message(self):
        return self.json_response.get("detail", "Response is not a valid JSON")

    def __str__(self):
        return "status_code=%s error_code=%s %s" % (self.status_code, self.error_code, self.error_message)


class AppMetricNotSupportedError(Exception):
    """配置缺失或版本不支持，无法提供应用指标信息"""


class AppInstancesNotFoundError(Exception):
    """因获取 APP 实例信息失败，无法查询指标信息"""
