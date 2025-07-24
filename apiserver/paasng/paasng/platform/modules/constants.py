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

from typing import Dict, List

from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum

DEFAULT_ENGINE_APP_PREFIX = "bkapp"


class ModuleName(StrStructuredEnum):
    DEFAULT = "default"


class ExposedURLType(IntStructuredEnum):
    # eg: http://foo.com/region-bkapp-code-stag/
    SUBPATH = 1
    # eg: http://code.foo-apps.com/
    SUBDOMAIN = 2

    def to_string(self) -> str:
        return self.name.lower()


class SourceOrigin(IntStructuredEnum):
    """Source origin defines the origin of module's source code"""

    AUTHORIZED_VCS = EnumField(1, "Authorized VCS")
    BK_LESS_CODE = EnumField(2, "BK-Lesscode")
    S_MART = EnumField(3, "S-Mart")
    # 旧镜像应用(非云原生)
    IMAGE_REGISTRY = EnumField(4, "Image Registry")
    # Deprecated: 场景模板现已不再使用，仅保留用于占位，防止误用导致数据错误
    SCENE = EnumField(5, "Scene")
    # 仅托管镜像的云原生应用
    CNATIVE_IMAGE = EnumField(6, "CNative Image")
    # AI agent 工具应用，使用蓝鲸 AI 平台提供的源码包部署
    AI_AGENT = EnumField(7, "AI Agent")

    @classmethod
    def get_default_origins(cls) -> List["SourceOrigin"]:
        return [SourceOrigin.AUTHORIZED_VCS, SourceOrigin.IMAGE_REGISTRY, SourceOrigin.CNATIVE_IMAGE]

    @classmethod
    def get_package_origins(cls) -> List["SourceOrigin"]:
        return [SourceOrigin.BK_LESS_CODE, SourceOrigin.S_MART, SourceOrigin.AI_AGENT]


class AppCategory(StrStructuredEnum):
    """Application category, used when setting label to images"""

    NORMAL_APP = "normal_app"
    S_MART_APP = "smart_app"
    CNATIVE_APP = "cnative_app"
    LEGACY_APP = "legacy_app"


class DeployHookType(StrStructuredEnum):
    """DeployHook Type"""

    PRE_RELEASE_HOOK = EnumField("pre-release-hook", label="部署前置钩子")

    @classmethod
    def _missing_(cls, value):
        # 兼容 value = pre_release_hook 的场景
        if value == "pre_release_hook":
            return cls.PRE_RELEASE_HOOK
        return super()._missing_(value)


class BuildPackType(StrStructuredEnum):
    # heroku buildpack format, just a tarball
    TAR = EnumField("tar", label="tar")
    # cnb remote buildpack format
    TGZ = EnumField("tgz", label="tgz")

    # oci-embedded is a virtual type, just used to enable user select buildpack embedded in builder image
    OCI_EMBEDDED = EnumField("oci-embedded", label="oci-embedded")
    # cnb buildpack OCI format, support "image" or "file"
    # TODO?: 在将 cnb buildpack 已镜像或文件形式分发到公共储存后，让 cnb-builder-shim 支持从远程地址拉群 buildpack
    # P.S. cnb 不强制要求将 buildpack 打到 builder 镜像里, 现在这样做只是没有公共存储可用，打到镜像里省事
    OCI_IMAGE = EnumField("oci-image", label="oci-image")
    OCI_FILE = EnumField("oci-file", label="oci-file")

    @classmethod
    def get_buildpack_builder_type_map(cls) -> Dict["BuildPackType", "AppImageType"]:
        return {
            cls.TAR: AppImageType.LEGACY,
            cls.TGZ: AppImageType.CNB,
            cls.OCI_IMAGE: AppImageType.CNB,
            cls.OCI_FILE: AppImageType.CNB,
            cls.OCI_EMBEDDED: AppImageType.CNB,
        }


class AppImageType(StrStructuredEnum):
    LEGACY = EnumField("legacy", label="legacy")
    CNB = EnumField("cnb", label="cnb")

    @classmethod
    def get_builder_buildpack_type_map(cls) -> Dict["AppImageType", List["BuildPackType"]]:
        return {
            cls.LEGACY: [BuildPackType.TAR],
            cls.CNB: [
                BuildPackType.TGZ,
                BuildPackType.OCI_IMAGE,
                BuildPackType.OCI_EMBEDDED,
                BuildPackType.OCI_FILE,
            ],
        }
