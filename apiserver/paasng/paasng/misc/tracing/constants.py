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

# 每帧 LOCALS 变量最多展示数
LOCALS_PREVIEW_LIMIT = 16
# 单个变量 repr 最大长度，超出尾部截断
LOCAL_VALUE_MAX_LEN = 1024
# SOURCE 片段在崩溃行上下展开的行数
SOURCE_CONTEXT_CTX = 5
# 链式异常最多展开层数（不含根异常）
CHAIN_DEPTH_LIMIT = 2
# exception.message 总长度上限
MESSAGE_MAX_LEN = 512 * 1024
# 保存错误堆栈详情的 event 名称，避开 SDK 标准的 `exception`
DIAGNOSTIC_EVENT_NAME = "exception.diagnostic"
