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

from typing import List, Optional

from pydantic import BaseModel, Field

from paasng.utils.structure import prepare_json_field


@prepare_json_field
class Pipeline(BaseModel):
    """流水线对象

    :param projectId: 项目ID
    :param pipelineId: 流水线ID
    """

    projectId: str
    pipelineId: str


@prepare_json_field(by_alias=False)
class PipelineBuild(BaseModel):
    """流水线构建对象

    :param projectId: 项目ID
    :param pipelineId: 流水线ID
    :param buildId: 构建ID
    """

    projectId: str
    pipelineId: str
    buildId: str = Field(alias="id")

    class Config:
        allow_population_by_field_name = True


@prepare_json_field
class TimeCost(BaseModel):
    """构建阶段耗时详情

    :param systemCost: 系统耗时（由总耗时减去其他得出）
    :param executeCost: 执行耗时
    :param waitCost: 等待耗时
    :param queueCost: 排队耗时（流水线并发、Stage下Job并发和Job互斥）
    :param totalCost: 总耗时（结束时间-开始时间）
    """

    systemCost: int
    executeCost: int
    waitCost: int
    queueCost: int
    totalCost: int


@prepare_json_field
class BuildStageStatus(BaseModel):
    """构建阶段状态

    :param stageId: 阶段ID
    :param name: 阶段名称
    :param status: 阶段状态
    :param startEpoch: 阶段启动时间
    :param elapsed: 容器运行时间
    :param showMsg: 展示信息
    """

    stageId: str
    name: str
    status: Optional[str]
    startEpoch: Optional[int]
    elapsed: Optional[int]
    showMsg: Optional[str]


@prepare_json_field
class PipelineBuildStatus(BaseModel):
    """流水线构建状态

    :param buildId: 构建ID
    :param startTime: 开始时间
    :param endTime: 结束时间
    :param status: 状态
    :param currentTimestamp: 服务器当前时间戳
    :param stageStatus: 各阶段状态
    :param totalTime: 总耗时(毫秒)
    :param executeTime: 运行耗时(毫秒，不包括人工审核时间)
    """

    buildId: str = Field(alias="id")
    startTime: int
    endTime: Optional[int]
    status: str
    currentTimestamp: str
    stageStatus: List[BuildStageStatus] = Field(default_factory=list)
    totalTime: Optional[int] = 0
    executeTime: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True


@prepare_json_field
class AdditionalOptions(BaseModel):
    """流水线构建状态额外配置

    :param elementPostInfo: 后置状态信息，如果存在这个字段说明这个步骤是后置步骤，前端不展示出来
    """

    elementPostInfo: Optional[dict]

    class Config:
        allow_population_by_field_name = True


@prepare_json_field(by_alias=False)
class PipelineElementModel(BaseModel):
    """流水线元素模型

    :param type: Element 类型
    :param name: 任务名称
    :param elementId: 任务ID
    :param status: 任务状态

    :param errorType: 错误类型
    :param errorCode: 错误代码
    :param errorMsg: 错误信息

    :param timeCost: 各项耗时
    """

    type: str = Field(alias="@type")
    elementId: str = Field(alias="id")
    name: str

    status: Optional[str]
    startEpoch: Optional[int]
    elapsed: Optional[int]

    errorType: Optional[str]
    errorCode: Optional[int]
    errorMsg: Optional[str]
    timeCost: Optional[TimeCost]

    additionalOptions: Optional[AdditionalOptions]

    class Config:
        allow_population_by_field_name = True


@prepare_json_field(by_alias=False)
class PipelineContainerModel(BaseModel):
    """流水线容器模型

    :param type: 容器模型类型
    :param containerId: 容器ID
    :param name: 容器名称
    :param status: 状态
    """

    type: str = Field(alias="@type")
    containerId: str = Field(alias="id")
    name: Optional[str]
    status: Optional[str]
    jobId: Optional[str]
    timeCost: Optional[TimeCost]
    elements: List[PipelineElementModel]

    class Config:
        allow_population_by_field_name = True


@prepare_json_field(by_alias=False)
class PipelineStageModel(BaseModel):
    """流水线阶段模型

    :param stageId: 阶段ID
    :param name: 阶段名称
    :param status: 阶段状态
    :param startEpoch: 阶段启动时间
    :param elapsed: 容器运行时间
    :param isFinally: 是否最终 stage
    :param containers: 容器集合, 目前约定一个 stage 只能有一个容器
    """

    stageId: str = Field(alias="id")
    name: str
    status: Optional[str]
    startEpoch: Optional[int]
    elapsed: Optional[int]
    isFinally: bool = Field(alias="finally")
    containers: List[PipelineContainerModel]

    class Config:
        allow_population_by_field_name = True


@prepare_json_field
class PipelineModel(BaseModel):
    """流水线模型

    :param name: 流水线名称
    :param desc: 流水线描述
    :param stages: 流水线节点集合
    :param timeCost: 各项执行耗时
    """

    name: str
    desc: str
    stages: List[PipelineStageModel]
    timeCost: Optional[TimeCost]


@prepare_json_field(by_alias=False)
class PipelineBuildDetail(BaseModel):
    """流水线构建详情

    :param buildId: 构建ID
    :param pipelineId: 流水线ID
    :param pipelineName: 流水线名称
    :param startTime: 启动时间
    :param endTime: 结束时间
    :param currentTimestamp: 服务器当前时间戳
    :param buildNum: 构建号
    :param model: 流水线模型
    """

    buildId: str = Field(alias="id")
    pipelineId: str
    pipelineName: str
    startTime: int
    endTime: Optional[int]
    status: str
    currentTimestamp: str
    buildNum: int
    model: PipelineModel

    class Config:
        allow_population_by_field_name = True


@prepare_json_field
class PipelineLogLine(BaseModel):
    """流水线构建

    :param lineNo: 日志行号
    :param timestamp: 日志时间戳
    :param message: 日志消息体
    :param priority: 日志权重级
    :param tag: 日志tag
    :param subTag: 日志子tag
    :param jobId: 日志jobId
    :param executeCount: 日志执行次数
    """

    lineNo: int
    timestamp: int
    message: str
    priority: str
    tag: str
    subTag: str
    jobId: str
    executeCount: int


@prepare_json_field
class PipelineLogModel(BaseModel):
    """流水线构建日志

    :param buildId: 构建日志
    :param finished: 是否结束
    :param hasMore: 是否结束
    :param logs: 日志列表
    :param timeUsed: 所用时间
    """

    buildId: str
    finished: bool
    hasMore: Optional[bool]
    logs: List[PipelineLogLine]
    timeUsed: Optional[int]


@prepare_json_field
class CodeccPluginBasicInfo(BaseModel):
    """Codecc 工具插件基本信息

    :param name: 插件标识
    :param displayName: 插件名称
    :param devLanguage: 开发语言
    :param toolCnTypes: 工具类别
    :param langList: 适用语言
    :param needBuildScript: 业务编译脚本, True: 需要业务提供, False: 不需要业务提供
    :param checkerNum: 规则数
    :param description: 工具描述
    """

    name: Optional[str] = None
    displayName: Optional[str] = None
    checkerNum: Optional[int] = None
    devLanguage: Optional[str] = None
    toolCnTypes: Optional[List[str]] = []
    langList: Optional[List[str]] = []
    needBuildScript: Optional[bool] = False
    description: Optional[str] = ""
