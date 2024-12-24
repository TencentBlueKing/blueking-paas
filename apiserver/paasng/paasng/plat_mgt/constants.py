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

# 敏感信息掩码（注：7 位 * 是故意的，避免遇到用户输入 6/8 位 * 的情况）
# 适用场景：平台管理 - 配置更新功能时，不对用户暴露数据库中的值（返回 MASK），用户提交 MASK 值
# 不会对数据库中的值进行修改，避免出现修改非 MASK 的配置时，还需要填写所有 MASK 值的情况（体验优化）
SENSITIVE_MASK = "*******"
