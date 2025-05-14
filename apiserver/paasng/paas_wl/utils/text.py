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

import base64

# URL path variables
PVAR_REGION = "(?P<region>[a-z0-9_-]{1,32})"
PVAR_NAME = "(?P<name>[a-z0-9_-]{1,64})"
PVAR_CLUSTER_NAME = "(?P<name>[a-z0-9_-]{1,64})"

# This pattern is widely used by kubernetes
DNS_SAFE_PATTERN = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"


def b64encode(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def b64decode(text: str) -> str:
    return base64.b64decode(text.encode()).decode()
