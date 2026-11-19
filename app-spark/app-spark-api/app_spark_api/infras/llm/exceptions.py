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

"""Errors raised while building or calling an LLM."""


class LLMError(Exception):
    """Base of every error this package raises.

    Messages are for operators. They never contain an API key or an access_token, nor the
    vendor's response body, so they are safe to log.
    """


class LLMConfigurationError(LLMError):
    """The model configuration names something that cannot be called, e.g. an unknown provider."""


class LLMCallError(LLMError):
    """The model was unreachable, refused the request, or answered nothing usable."""
