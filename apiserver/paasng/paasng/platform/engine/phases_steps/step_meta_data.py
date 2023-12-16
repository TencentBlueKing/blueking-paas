# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Dict, List, Optional

from attrs import define

from paasng.platform.engine.models import DeployPhaseTypes


@define
class StepMetaData:
    name: str
    display_name_en: str
    display_name_zh_cn: str
    phase: str
    started_patterns: Optional[List[str]] = None
    finished_patterns: Optional[List[str]] = None

    def __attrs_post_init__(self):
        if self.name in ALL_STEP_METAS:
            raise ValueError(f"Duplicate step name: {self.name}")

        ALL_STEP_METAS[self.name] = self


ALL_STEP_METAS: Dict[str, StepMetaData] = {}

###### Phase: PREPARATION ######
PARSE_APP_PROCESS = StepMetaData(
    name="解析应用进程信息",
    display_name_en="Parse app process",
    display_name_zh_cn="解析应用进程信息",
    phase=DeployPhaseTypes.PREPARATION.value,
)


UPLOAD_CODE = StepMetaData(
    name="上传仓库代码",
    display_name_en="Upload repository code",
    display_name_zh_cn="上传仓库代码",
    phase=DeployPhaseTypes.PREPARATION.value,
)

CONFIG_RESOURCE_INSTANCE = StepMetaData(
    name="配置资源实例",
    display_name_en="Config resource instance",
    display_name_zh_cn="配置资源实例",
    phase=DeployPhaseTypes.PREPARATION.value,
)

###### Phase: RELEASE ######
DEPLOY_APP = StepMetaData(
    name="部署应用",
    display_name_en="Deploying the app",
    display_name_zh_cn="部署应用",
    phase=DeployPhaseTypes.RELEASE.value,
)

EXECUTE_PRE_RELEASE = StepMetaData(
    name="执行部署前置命令",
    display_name_en="Execute Pre-release cmd",
    display_name_zh_cn="执行部署前置命令",
    phase=DeployPhaseTypes.RELEASE.value,
)

CHECK_DEPLOY_RESULT = StepMetaData(
    name="检测部署结果",
    display_name_en="View Deploy results",
    display_name_zh_cn="检测部署结果",
    phase=DeployPhaseTypes.RELEASE.value,
)

###### Phase: BUILD ######
INITIALIZE_BUILD_ENV = StepMetaData(
    name="初始化构建环境",
    display_name_en="Initialize build environment",
    display_name_zh_cn="初始化构建环境",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Step setup begin", "Setup Build Environ"],
    finished_patterns=[r"\s+Step setup done", r"\s+Starting builder..."],
)

DETECT_BUILDPACK = StepMetaData(
    name="检测构建工具",
    display_name_en="Detect buildpack",
    display_name_zh_cn="检测构建工具",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Step detect begin", "Detecting Buildpacks..."],
    finished_patterns=[r"\s+Step detect done", r"\s+Step Detect done"],
)

ANALYZE_BUILD = StepMetaData(
    name="分析构建方案",
    display_name_en="Analyze build solutions",
    display_name_zh_cn="分析构建方案",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Step analysis begin", "Analyzing optimization plan"],
    finished_patterns=[r"\s+Step analysis done", r"\s+Step Analyze done"],
)

CALL_PRE_COMPILE = StepMetaData(
    name="调用 pre-compile",
    display_name_en="Calling pre-compile",
    display_name_zh_cn="调用 pre-compile",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Running pre-compile hook"],
)

CALL_POST_COMPILE = StepMetaData(
    name="调用 post-compile",
    display_name_en="Calling post-compile",
    display_name_zh_cn="调用 post-compile",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Running post-compile hook"],
)

BUILD_APP = StepMetaData(
    name="构建应用",
    display_name_en="Building Applications",
    display_name_zh_cn="构建应用",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Compiling app...", "-----> Step build begin", "Building application..."],
    finished_patterns=["-----> Discovering process types", r"\s+Step build done", r"\s+Step Build done"],
)

GENERATE_BUILD_RESULT = StepMetaData(
    name="生成构建结果",
    display_name_en="Generate build results",
    display_name_zh_cn="生成构建结果",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Step export begin"],
    finished_patterns=[r"\s+Step export done"],
)

CLEAN_BUILD_ENV = StepMetaData(
    name="清理构建环境",
    display_name_en="Clean build environment",
    display_name_zh_cn="清理构建环境",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Step finish begin"],
    finished_patterns=[r"\s+Step finish done"],
)

DOWNLOAD_CODE = StepMetaData(
    name="下载代码",
    display_name_en="Downloading code",
    display_name_zh_cn="下载代码",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["Downloading app source code"],
    finished_patterns=["Restoring cache..."],
)

RESTORE_CACHE = StepMetaData(
    name="加载缓存",
    display_name_en="Restoring cache",
    display_name_zh_cn="加载缓存",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["Restoring cache..."],
    finished_patterns=["-----> Compiling app..."],
)

DISCOVER_PROCESS_TYPES = StepMetaData(
    name="检测进程类型",
    display_name_en="Discover process types",
    display_name_zh_cn="检测进程类型",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Discovering process types"],
    finished_patterns=["-----> Compiled slug size is"],
)

MAKE_SLUG = StepMetaData(
    name="制作打包构件",
    display_name_en="Making slug package",
    display_name_zh_cn="制作打包构件",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["-----> Compiled slug size is"],
    finished_patterns=["Checking for changes inside the cache directory..."],
)

UPLOAD_CACHE = StepMetaData(
    name="上传缓存",
    display_name_en="Upload Cache",
    display_name_zh_cn="上传缓存",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["Checking for changes inside the cache directory..."],
    finished_patterns=["Done: Uploaded cache"],
)

UPLOAD_IMAGE = StepMetaData(
    name="上传镜像",
    display_name_en="Upload image",
    display_name_zh_cn="上传镜像",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["Exporting image..."],
    finished_patterns=[r"\s+Step Export done"],
)

DOWNLOAD_DOCKER_BUILD_CTX = StepMetaData(
    name="下载构建上下文",
    display_name_en="Download docker build context",
    display_name_zh_cn="下载构建上下文",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["Downloading docker build context..."],
    finished_patterns=[r"\* Docker build context is ready"],
)

BUILD_IMAGE = StepMetaData(
    name="构建镜像",
    display_name_en="Building image",
    display_name_zh_cn="构建镜像",
    phase=DeployPhaseTypes.BUILD.value,
    started_patterns=["Start building..."],
    finished_patterns=[r"\* Build success"],
)


DEFAULT_SET = [
    # prepare
    PARSE_APP_PROCESS,
    UPLOAD_CODE,
    CONFIG_RESOURCE_INSTANCE,
    # build
    DOWNLOAD_CODE,
    RESTORE_CACHE,
    BUILD_APP,
    DISCOVER_PROCESS_TYPES,
    MAKE_SLUG,
    UPLOAD_CACHE,
    # release
    EXECUTE_PRE_RELEASE,
    DEPLOY_APP,
    CHECK_DEPLOY_RESULT,
]

SLUG_PILOT_SET = [
    # prepare
    PARSE_APP_PROCESS,
    UPLOAD_CODE,
    CONFIG_RESOURCE_INSTANCE,
    # build
    INITIALIZE_BUILD_ENV,
    DETECT_BUILDPACK,
    ANALYZE_BUILD,
    CALL_PRE_COMPILE,
    BUILD_APP,
    CALL_POST_COMPILE,
    GENERATE_BUILD_RESULT,
    CLEAN_BUILD_ENV,
    # release
    EXECUTE_PRE_RELEASE,
    DEPLOY_APP,
    CHECK_DEPLOY_RESULT,
]

CNB_SET = [
    # prepare
    PARSE_APP_PROCESS,
    UPLOAD_CODE,
    CONFIG_RESOURCE_INSTANCE,
    # build
    INITIALIZE_BUILD_ENV,
    ANALYZE_BUILD,
    DETECT_BUILDPACK,
    BUILD_APP,
    UPLOAD_IMAGE,
    # release
    DEPLOY_APP,
    EXECUTE_PRE_RELEASE,
    CHECK_DEPLOY_RESULT,
]

DOCKER_BUILD_SET = [
    # prepare
    PARSE_APP_PROCESS,
    UPLOAD_CODE,
    CONFIG_RESOURCE_INSTANCE,
    # build
    DOWNLOAD_DOCKER_BUILD_CTX,
    BUILD_IMAGE,
    # release
    DEPLOY_APP,
    EXECUTE_PRE_RELEASE,
    CHECK_DEPLOY_RESULT,
]

IMAGE_RELEASE_SET = [
    # prepare
    PARSE_APP_PROCESS,
    CONFIG_RESOURCE_INSTANCE,
    # release
    DEPLOY_APP,
    EXECUTE_PRE_RELEASE,
    CHECK_DEPLOY_RESULT,
]
