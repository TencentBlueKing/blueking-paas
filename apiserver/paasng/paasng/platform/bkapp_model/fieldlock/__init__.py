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

"""fieldlock 模块存放所有与 bkapp model 字段锁定(更新)相关的逻辑

Q: 什么场景下需要启用字段锁定功能?
A: 当用户通过 app_desc（应用描述文件）部署应用时，系统会将描述文件解析为资源实体（bkapp entity），继而通过 entities_syncer 模块将变更同步
至对应的 bkapp model 中. 然而, 有时用户希望保留 bkapp model 中现有的部分字段值，禁止通过 app_desc 的更新覆盖这些字段，则需启用字段锁定功能.
例如，用户已通过页面配置了生产环境的副本数，不希望每次因 app_desc 的修改而更新副本值.

Q: 字段锁定的实现原理?
A: 基于 entities_syncer 模块中已有的更新策略, 可以通过两种方式完成字段锁定: 一种是不更新, 另外一种是原值回写. generate_locked_xx_values
函数根据这两种方式, 为应用的模块生成 locked_values (锁定值). 应用模块的 bkapp entity 依据 locked_values, 替换相应的字段,
再通过 entities_syncer 同步时, 会完成字段锁定.

方案的优势: 在原 entities_syncer 的更新策略之上不额外增加锁定逻辑, 并且通过一致的同步流程, 确保字段的管理者也不受影响.
"""
