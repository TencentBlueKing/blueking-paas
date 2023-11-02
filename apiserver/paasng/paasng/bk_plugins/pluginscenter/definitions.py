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
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from paasng.utils.structure import register


@register
class UIComponent(BaseModel):
    """ui组件"""

    name: str
    props: Dict = Field(default_factory=dict)


@register
class UIProps(BaseModel):
    """ui属性"""

    required: bool


@register(exclude_none=True)
class FieldSchema(BaseModel):
    """字段定义"""

    type: Literal["string", "array"] = Field(default="string", description="字段类型")
    title: str = Field(default="", description="字段标题")
    description: str = Field(default="", description="该字段的说明提示")
    pattern: Optional[str] = Field(description="该字段匹配的正则表达式模板")
    default: Optional[Any] = Field(description="默认值")
    maxlength: Optional[int] = Field(description="最大长度")
    uiComponent: Optional[UIComponent] = Field(alias="ui:component")
    uiValidator: Optional[List] = Field(alias="ui:validator")
    uiProps: Optional[UIProps] = Field(alias="ui:props")
    uiReactions: Optional[List] = Field(alias="ui:reactions")
    items: Optional[Dict] = Field(alias="items")


@register
class PluginBackendAPIResource(BaseModel):
    """插件后台操作接口"""

    apiName: str = Field(description="网关名称")
    path: str = Field(description="接口路径")
    method: Literal["GET", "POST", "PUT", "DELETE"]

    class Config:
        frozen = True


@register
class PluginBackendAPI(BaseModel):
    create: Optional[PluginBackendAPIResource]
    read: Optional[PluginBackendAPIResource]
    update: Optional[PluginBackendAPIResource]
    delete: Optional[PluginBackendAPIResource]


@register
class PluginReleaseAPI(BaseModel):
    """插件发布操作集"""

    release: Optional[PluginBackendAPIResource] = Field(description="部署/构建操作")
    result: PluginBackendAPIResource = Field(description="查询是否可进入下一步")
    log: Optional[PluginBackendAPIResource] = Field(description="日志接口")


@register
class PluginCodeTemplate(BaseModel):
    id: str = Field(description="模板id")
    name: str = Field(description="模板名称")
    language: str = Field(description="开发语言")
    applicableLanguage: Optional[str] = Field(default=None, description="适用语言")
    repository: str = Field(description="仓库地址")
    sourceDir: str = Field(default="./", description="源码目录")

    def get_source_dir(self) -> Path:
        """get relative source_dir"""
        source_dir = Path(self.sourceDir)
        if source_dir.is_absolute():
            return source_dir.relative_to("/")
        return source_dir


@register
class PluginFeature(BaseModel):
    name: str = Field(description="功能特性名称")
    value: bool = Field(default=False, description="功能特性开关")


@register
class PluginBasicInfoDefinition(BaseModel):
    """插件基础信息定义"""

    id: FieldSchema = Field(description="插件 ID")
    name: FieldSchema = Field(description="插件名称")
    releaseMethod: Literal["code", "sourcePackage", "image"] = Field(description="插件发布方式")
    initTemplates: List[PluginCodeTemplate] = Field(description="插件初始化模板")
    repositoryGroup: str = Field(description="插件代码初始化仓库组")
    extraFields: Dict[str, FieldSchema] = Field(default_factory=dict)
    api: PluginBackendAPI = Field(description="基础信息操作接口集")
    syncMembers: PluginBackendAPIResource = Field(description="人员同步接口")


@register
class PluginVisibleRangeLevel(BaseModel):
    """插件可见范围级别"""

    name: str
    id: str
    type: Literal["department"]


@register
class PluginVisibleRangeDefinition(BaseModel):
    """插件可见范围"""

    enabled: bool = Field(False, description="应用可见范围开关")
    tips: str = Field(description="可见范围提示语")
    scope: Literal["organization", "project", "business"]
    topLevel: PluginVisibleRangeLevel


@register
class PluginMarketInfoDefinition(BaseModel):
    """插件市场信息定义"""

    storage: Literal["third-party", "platform", "both"] = Field(
        description="市场信息存储方式, "
        "third-party(仅存储在第三方系统, 需提供 read API)、"
        "platform(仅存储在插件开发中心)、"
        "both(插件开发中心和第三方系统都存储, 需提供 create/update API)"
    )
    category: PluginBackendAPIResource = Field(description="市场类型分类查询接口")
    api: Optional[PluginBackendAPI] = Field(description="插件市场信息操作接口集")
    extraFields: Dict[str, FieldSchema] = Field(default_factory=dict)
    # TODO: visibleRange


@register
class ReleaseRevisionDefinition(BaseModel):
    """发布版本定义"""

    revisionType: Literal["all", "master", "tag"] = Field(description="代码版本类型(all, 不限制; master 仅可选择主分支发布; tag Tag发布)")
    revisionPattern: Optional[str] = Field(description="代码版本正则表达式模板, 留空则不校验")
    docs: Optional[str] = Field(description="代码版本校验失败的指引文档")
    versionNo: Literal["automatic", "revision", "commit-hash", "self-fill"] = Field(
        description="版本号生成规则, 自动生成(automatic)," "与代码版本一致(revision)," "与提交哈希一致(commit-hash)," "用户自助填写(self-fill)"
    )
    extraFields: Dict[str, FieldSchema] = Field(default_factory=dict)
    api: Optional[PluginBackendAPI] = Field(description="发布版本-操作接口集, 如需要回调至第三方系统, 则需要提供 create 接口")


@register
class ReleaseStageDefinition(BaseModel):
    """发布阶段定义"""

    id: str
    name: str
    invokeMethod: Literal["deployAPI", "pipeline", "subpage", "itsm", "builtin"] = Field(description="触发方式")
    api: Optional[PluginReleaseAPI] = Field(description="类型为 api/subpage 时必填")
    pipelineId: Optional[str] = Field(description="类型为 pipeline 时必填")
    pageUrl: Optional[str] = Field(description="类型为 subpage 时必填")
    pipelineParams: Optional[Dict] = Field(description="蓝盾流水线调用参数模板")
    itsmServiceName: Optional[str] = Field(description="itsm 服务名称, 类型为 itsm 时必填")
    builtinParams: Optional[Dict] = Field(description="内置阶段额外参数(完善市场信息market, 灰度grayScale, 上线online)")


@register
class PluginConfigColumnDefinition(BaseModel):
    """插件配置-列信息定义"""

    type: Literal["string"] = Field(default="string", description="字段类型")
    name: str = Field(description="该字段对应的变量名")
    title: str = Field(default="", description="字段标题")
    description: str = Field(default="", description="该字段的说明提示")
    pattern: Optional[str] = Field(description="该字段匹配的正则表达式模板")
    options: Optional[Dict[str, str]] = Field(description="该字段的选项")
    unique: bool = Field(False, description="该列是否唯一(多列同时标记唯一时仅支持 unique_together)")


@register
class PluginConfigDefinition(BaseModel):
    """插件配置定义"""

    title: str = Field(default="配置管理", description="「配置管理」标题")
    description: str = Field(default="", description="插件类型描述")
    docs: str = Field(default="", description="插件类型说明文档")
    syncAPI: PluginBackendAPIResource = Field(description="「配置管理」同步接口")
    columns: List[PluginConfigColumnDefinition] = Field(default_factory=list, min_items=1)


@register
class PluginInstanceSpec(BaseModel):
    """插件实例相关属性"""

    basicInfo: PluginBasicInfoDefinition
    marketInfo: PluginMarketInfoDefinition
    configInfo: Optional[PluginConfigDefinition] = Field(description="「配置管理」功能相关配置")


@register
class ElasticSearchHost(BaseModel):
    """ES 配置"""

    host: str
    port: int
    http_auth: str = Field(..., alias="httpAuth", description="形如 username:password 的凭证对")
    url_prefix: str = Field("", alias="urlPrefix")
    use_ssl: bool = Field(False, alias="useSSL")


@register
class ElasticSearchParams(BaseModel):
    """ES 搜索相关配置"""

    indexPattern: str = Field(description="索引模板")
    timeField: str = Field(default="@timestamp", description="时间字段")
    timeFormat: Literal["timestamp[s]", "timestamp[ns]", "datetime"] = Field(default="timestamp[s]")
    messageField: str = Field(default="json.message", description="消息字段")
    termTemplate: Dict[str, str] = Field(
        description="搜索语句模板, 插件开发中心默认使用 plugin_id: {{ plugin_id }} 作为日志的过滤条件, 配置 fieldMapping 可重载这个过滤条件;"
    )
    builtinFilters: Dict[str, Union[str, List[str]]] = Field(default_factory=dict, description="内置的过滤条件")
    builtinExcludes: Dict[str, Union[str, List[str]]] = Field(default_factory=dict, description="内置的排除条件")
    # paas 的标准输出日志过滤条件
    # termTemplate = {"app_code": "{{ plugin_id }}"}
    # builtinFilters = {"environment": "prod", "stream": ["stderr", "stdout"]}

    # paas 的结构化日志过滤条件
    # termTemplate = {"app_code": "{{ plugin_id }}"}
    # builtinFilters = {"environment": "prod"}
    # builtinExcludes = {"stream": ["stderr", "stdout"]}

    # udc 的日志过滤条件
    # termTemplate = {"udc_name": "{{ plugin_id }}"}


class BKLogConfig(BaseModel):
    """日志平台的查询配置"""

    scenarioID: Literal["log", "bkdata"] = Field(default="log", description="接入场景")
    bkdataDataToken: Optional[str] = Field(description="数据平台认证Token")
    bkdataAuthenticationMethod: Optional[Literal["token", "user"]] = Field(description="数据平台认证方式")


@register
class PluginLogConfig(BaseModel):
    """插件日志配置"""

    backendType: Literal["es", "bkLog"] = Field(description="插件后端类型")
    elasticSearchHosts: Optional[List[ElasticSearchHost]] = Field(
        min_items=1, description="required when backend_type is 'es'"
    )
    bkLogConfig: Optional[BKLogConfig] = Field(description="required when backend_type is 'bkLog'")
    stdout: ElasticSearchParams
    ingress: Optional[ElasticSearchParams]
    json_: Optional[ElasticSearchParams] = Field(alias="json")


@register
class PluginCreateApproval(BaseModel):
    """创建插件审批配置"""

    enabled: bool = Field(default=False, description="是否开启创建审批流程")
    tips: str = Field(default="", description="审批流程提示语")
    docs: str = Field(default="", description="审批流程说明文档")
    itsmServiceName: str = Field(default="", description="审批流程 itsm 服务名称")


@register
class PluginDefinition(BaseModel):
    """插件模板定义"""

    identifier: str = Field(description="插件类型唯一标识", alias="id")
    name: str = Field(description="插件类型名称")
    description: str = Field(description="插件类型描述")
    docs: str = Field(description="插件类型说明文档")
    logo: str = Field(description="插件logo链接")
    spec: PluginInstanceSpec = Field(description="插件实例相关属性")
    administrator: List[str] = Field(description="插件管理员(负责创建审批、上线审批), 内容需要使用 bkpaas_auth 编码")
    approvalConfig: Optional[PluginCreateApproval] = Field(description="插件创建审批配置")
    releaseRevision: ReleaseRevisionDefinition = Field(description="插件发布版本规则")
    releaseStages: List[ReleaseStageDefinition] = Field(description="插件发布步骤")
    logConfig: Optional[PluginLogConfig] = Field(description="插件运行过程的日志配置")
    features: List[PluginFeature] = Field(default_factory=list)


def find_stage_by_id(
    release_stages: List[ReleaseStageDefinition], identifier: str
) -> Optional[ReleaseStageDefinition]:
    for stage in release_stages:
        if stage.id == identifier:
            return stage
    return None
