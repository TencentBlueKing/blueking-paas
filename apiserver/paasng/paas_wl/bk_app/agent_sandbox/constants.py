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

# ================================
# Constants for "K8s Pod Sandbox"
# ================================

# The Default image for running k8s pod sandbox
DEFAULT_IMAGE = "python:3.11-alpine"
# The default working directory in sandbox container
DEFAULT_WORKDIR = "/workspace"
# The default command to keep the sandbox pod alive
DEFAULT_COMMAND = ["/bin/sh", "-c", "sleep 36000"]
# The default termination grace period seconds for sandbox pod
DEFAULT_TERMINATION_GRACE_PERIOD_SECONDS = 3
# The default resource specification for sandbox pod
DEFAULT_RESOURCES = {
    "limits": {"cpu": "2000m", "memory": "512Mi"},
    "requests": {"cpu": "100m", "memory": "128Mi"},
}
