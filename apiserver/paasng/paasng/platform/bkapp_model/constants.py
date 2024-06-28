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

# legacy: Slug runner 默认的 entrypoint, 平台所有 slug runner 镜像都以该值作为入口
# TODO: 需验证存量所有镜像是否都设置了默认的 entrypoint, 如是, 即可移除所有 DEFAULT_SLUG_RUNNER_ENTRYPOINT
DEFAULT_SLUG_RUNNER_ENTRYPOINT = ["bash", "/runner/init"]
