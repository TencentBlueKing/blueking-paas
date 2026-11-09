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

"""Project 生命周期里供其他模块挂接的信号，免得 core 反过来依赖它们。"""

from django.dispatch import Signal

# 删除 Project 时、清理任何资源之前发出（asend），参数为 project。receiver 用来让挂在项目上的后台任务收手；
# 失败时抛 ProjectDeletionError 说明是哪类资源，删除就此中止。
project_deleting = Signal()
