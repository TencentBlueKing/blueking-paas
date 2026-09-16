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

# Project ID 由调用方指定，所以它的形状必须在入口处卡死，而不只是「建议这么写」。
#
# 首字符限定为字母，是为了避免出现纯数字 ID——那种 ID 在 URL 和日志里很容易被当成别的东西。
# 长度 2-20，上限对齐 `Project.id` 的 max_length。
PROJECT_ID_PATTERN = r"^[a-z][a-z0-9-]{1,19}$"
