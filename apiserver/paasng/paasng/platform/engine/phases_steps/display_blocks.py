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
from typing import TYPE_CHECKING, Dict, List, Type

from paasng.accessories.publish.entrance.preallocated import get_preallocated_url
from paasng.accessories.serializers import DocumentaryLinkSLZ
from paasng.accessories.smart_advisor.advisor import DocumentaryLinkAdvisor
from paasng.accessories.smart_advisor.tags import DeployPhaseTag
from paasng.platform.engine.models.phases import DeployPhaseTypes

if TYPE_CHECKING:
    from paasng.platform.engine.models import DeployPhase, EngineApp
    from paasng.platform.modules.helpers import ModuleRuntimeManager
    from paasng.platform.modules.models import Module


class DisplayBlock:
    """标准化的应用信息展示"""

    name: str = ""

    @staticmethod
    def get_module_by_engine_app(engine_app: "EngineApp") -> "Module":
        return engine_app.env.module

    @classmethod
    def get_detail(cls, engine_app: "EngineApp") -> dict:
        raise NotImplementedError


class SourceInfo(DisplayBlock):
    name = "source_info"

    @classmethod
    def get_detail(cls, engine_app: "EngineApp") -> dict:
        from paasng.platform.sourcectl.serializers import RepositorySLZ

        module = cls.get_module_by_engine_app(engine_app)
        return {cls.name: RepositorySLZ(module.get_source_obj()).data}


class ServicesInfo(DisplayBlock):
    """展示增强服务信息"""

    name = "services_info"

    @classmethod
    def get_detail(cls, engine_app: "EngineApp") -> dict:
        from paasng.accessories.servicehub.manager import mixed_service_mgr

        detail = []
        for svc in mixed_service_mgr.list_binded(engine_app.env.module):  # type: ignore
            svc_info = dict(name=svc.name, display_name=svc.display_name)
            for rel in mixed_service_mgr.list_provisioned_rels(engine_app, svc):  # type: ignore
                svc_info.update(
                    {
                        "is_provisioned": rel.is_provisioned(),  # type: ignore
                        "service_id": rel.get_service().uuid,  # type: ignore
                        "category_id": rel.get_service().category_id,  # type: ignore
                    }
                )
            detail.append(svc_info)

        return {cls.name: detail}


class HelpDocs(DisplayBlock):
    name = "help_docs"
    deploy_phase = ""

    @classmethod
    def get_doc_links(cls):
        """当前我们只是简单的增加帮助文档的访问链接"""
        tag = DeployPhaseTag(cls.deploy_phase)
        advisor = DocumentaryLinkAdvisor()
        docs = advisor.search_by_tags([tag])

        return DocumentaryLinkSLZ(docs, many=True).data

    @classmethod
    def get_detail(cls, engine_app: "EngineApp") -> dict:
        return {cls.name: cls.get_doc_links()}


class PrepareHelpDocs(HelpDocs):
    """展示准备阶段帮助文档"""

    name = "prepare_help_docs"
    deploy_phase = "prepare"


class BuildHelpDocs(HelpDocs):
    """展示构建阶段帮助文档"""

    name = "build_help_docs"
    deploy_phase = "build"


class ReleaseHelpDocs(HelpDocs):
    """展示发布阶段帮助文档"""

    name = "release_help_docs"
    deploy_phase = "release"


class RuntimeInfo(DisplayBlock):
    """展示运行时信息"""

    name = "runtime_info"

    @classmethod
    def get_module_runtime_manager(cls, engine_app: "EngineApp") -> "ModuleRuntimeManager":
        from paasng.platform.modules.helpers import ModuleRuntimeManager

        return ModuleRuntimeManager(cls.get_module_by_engine_app(engine_app))

    @classmethod
    def get_detail(cls, engine_app: "EngineApp") -> dict:
        from paasng.platform.modules.serializers import ModuleRuntimeSLZ

        m = cls.get_module_runtime_manager(engine_app)
        slugbuilder = m.get_slug_builder(raise_exception=False)
        buildpacks = m.list_buildpacks()
        if not slugbuilder or not buildpacks:
            return {}

        return {cls.name: ModuleRuntimeSLZ(dict(buildpacks=buildpacks, image=slugbuilder.display_name)).data}


class AccessInfo(DisplayBlock):
    """展示访问域名信息"""

    name = "access_info"

    @classmethod
    def get_detail(cls, engine_app: "EngineApp") -> dict:
        info = get_preallocated_url(engine_app.env)
        if info is None:
            return {}

        return {cls.name: dict(address=info.address, type=info.provider_type)}


def get_display_blocks_by_type(phase_type: DeployPhaseTypes) -> List[Type[DisplayBlock]]:
    """Get display blocks by deploy phase type

    :param phase_type: The deploy phase type
    :return: A list of display block types
    """
    map_: Dict[DeployPhaseTypes, List[Type[DisplayBlock]]] = {
        DeployPhaseTypes.PREPARATION: [SourceInfo, ServicesInfo, PrepareHelpDocs],
        DeployPhaseTypes.BUILD: [RuntimeInfo, BuildHelpDocs],
        DeployPhaseTypes.RELEASE: [
            AccessInfo,
            ReleaseHelpDocs,
        ],
    }
    return map_[phase_type]


class DeployDisplayBlockRenderer:
    @staticmethod
    def get_display_blocks_info(phase_obj: "DeployPhase") -> dict:
        """获取该阶段的静态展示信息"""
        # Q: 为什么这里不直接存渲染后的内容？
        # A: 因为很多信息是没有办法在应用创建拿到的，如果要存这些信息，那么需要引入信息及时同步的复杂度
        # 所以每次请求 deploy skeleton 时，都需要实时渲染一次
        info = dict()
        for b in get_display_blocks_by_type(DeployPhaseTypes(phase_obj.type)):
            info.update(b.get_detail(engine_app=phase_obj.engine_app))
        return info
