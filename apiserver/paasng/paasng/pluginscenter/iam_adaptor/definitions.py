"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import ClassVar, Optional

from attrs import define
from django.utils.translation import gettext as _

from paasng.pluginscenter.constants import PluginRole
from paasng.pluginscenter.iam_adaptor.constants import ResourceType
from paasng.pluginscenter.models import PluginInstance


@define
class GradeManager:
    """蓝鲸插件在 IMA 中对应的分级管理员定义"""

    name: str
    description: str


@define
class IAMResource:
    """IAM 资源定义"""

    resource_type: ClassVar[str] = ""
    id: str
    name: str

    @property
    def iam_attribute(self):
        return {}


@define
class PluginIAMResource(IAMResource):
    """蓝鲸插件在 IAM 中对应的资源定义"""

    resource_type: ClassVar[str] = ResourceType.PLUGIN
    admin: Optional[str] = None


@define
class PluginUserGroup:
    """蓝鲸插件在 IAM 中的用户组定义"""

    id: Optional[int]
    role: PluginRole
    name: str
    description: str


def gen_iam_grade_manager(plugin: PluginInstance) -> GradeManager:
    """生成蓝鲸插件在 IAM 的分级管理员描述"""
    return GradeManager(
        # 分级管理员名称（最大字符数限制 32）"
        name=f"{plugin.pd.name}:{plugin.id}",
        description=_('{pd_name}（{resource_name}）分级管理员，拥有审批用户加入管理者/开发者用户组权限。').format(
            pd_name=plugin.pd.name, resource_name=gen_iam_resource_name(plugin)
        ),
    )


def gen_iam_resource(plugin: PluginInstance) -> PluginIAMResource:
    return PluginIAMResource(
        id=gen_iam_resource_id(plugin), name=gen_iam_resource_name(plugin), admin=plugin.creator.username
    )


def gen_plugin_user_group(plugin: PluginInstance, role: PluginRole) -> PluginUserGroup:
    return PluginUserGroup(
        role=PluginRole(role),
        name=gen_user_group_name(plugin, role),
        description=gen_user_group_description(plugin, role),
        id=None,
    )


def gen_iam_resource_id(plugin: PluginInstance) -> str:
    """生成 IAM 资源唯一标识"""
    # warning: 需要保证资源唯一标识可反查出对应的 PluginInstance 实例
    return f"{plugin.pd.identifier}:{plugin.id}"


def gen_iam_resource_name(plugin: PluginInstance) -> str:
    """生成 IAM 资源名称"""
    return f"{plugin.name}({plugin.id})"


def gen_user_group_name(plugin: PluginInstance, role: PluginRole) -> str:
    """根据指定的用户角色，生成对应的用户组名称（最大字符数限制 32）"""
    # warning: IAM 未支持分组名称国际化, 这里使用 gettext 只在创建用户组时生效
    if role == PluginRole.ADMINISTRATOR:
        return _('{pd_name}-{plugin_name}-管理者').format(pd_name=plugin.pd.name, plugin_name=plugin.name)
    elif role == PluginRole.DEVELOPER:
        return _('{pd_name}-{plugin_name}-开发者').format(pd_name=plugin.pd.name, plugin_name=plugin.name)
    raise NotImplementedError


def gen_user_group_description(plugin: PluginInstance, role: PluginRole) -> str:
    """根据指定的用户角色，生成对应的用户组名称"""
    if role == PluginRole.ADMINISTRATOR:
        return _('{pd_name}（{plugin_name}）管理者，拥有应用的全部权限。').format(pd_name=plugin.pd.name, plugin_name=plugin.name)
    elif role == PluginRole.DEVELOPER:
        return _('{pd_name}（{plugin_name}）开发者，拥有应用的开发权限，如基础开发，版本发布等。').format(
            pd_name=plugin.pd.name, plugin_name=plugin.name
        )
    raise NotImplementedError
