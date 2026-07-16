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

from paas_wl.infras.resources.base.kres import BaseKresource


class SandboxInstance(BaseKresource):
    """CRD: SandboxInstance(sbi), 最小沙箱运行实例, 由集群侧 sandbox-controller 协调渲染 cube Pod。

    与 BkApp CR 一样, 本类仅复用底层通用的 dynamic client 下发能力
    (create_or_update / patch / get / delete), 不与 BkApp 的数据模型耦合。
    """

    kind = "SandboxInstance"
