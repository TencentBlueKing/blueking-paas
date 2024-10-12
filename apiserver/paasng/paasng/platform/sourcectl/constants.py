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

from blue_krill.data_types.enum import EnumField, FeatureFlagField, StructuredEnum

from paasng.infras.accounts.constants import AccountFeatureFlag


class DiffFeatureType(str, StructuredEnum):
    """代码对比类型"""

    INTERNAL = "internal"
    EXTERNAL = "external"


class BasicSourceType(str, StructuredEnum):
    """基础源码类型"""

    GIT = "git"
    SVN = "svn"
    PACKAGE = "package"


def register_new_sourcectl_type(feature_flag: FeatureFlagField):
    """暴露给 TE 版本的注册 SourcectlType 的方法

    :param name: 源码类型名称
    :param feature_flag: 用于控制该源码系统的黑/白名单
    """
    AccountFeatureFlag.register_ext_feature_flag(feature_flag)


class VersionType(str, StructuredEnum):
    """版本类型. 对应 VersionInfo.version_type"""

    TAG = EnumField("tag", label="用于 Git 仓库、云原生镜像应用、旧镜像应用、镜像模式的 S-Mart 应用")
    BRANCH = EnumField("branch", label="用于 SVN 仓库、Git 仓库")
    TRUNK = EnumField("trunk", label="用于 SVN 仓库")
    IMAGE = EnumField("image", label="仅用于云原生应用选择已构建的镜像部署时")
    PACKAGE = EnumField("package", label="用于 lesscode 应用和二进制的 S-Mart 应用")
