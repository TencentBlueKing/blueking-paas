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
import logging
import uuid
from typing import TYPE_CHECKING

from django.db import models

from paasng.dev_resources.sourcectl.source_types import get_sourcectl_names
from paasng.engine.constants import RuntimeType
from paasng.platform.modules.constants import SourceOrigin
from paasng.utils.models import BkUserField, OwnerTimestampedModel

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from paasng.dev_resources.sourcectl.models import RepositoryInstance


class Module(OwnerTimestampedModel):
    """Module for Application
    Every application has a default module. Application owner
    can create multiple modules to achieve a micro-services architecture
    """

    id = models.UUIDField('UUID', default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    application = models.ForeignKey('applications.Application', on_delete=models.CASCADE, related_name='modules')

    name = models.CharField(verbose_name=u'模块名称', max_length=20)
    is_default = models.BooleanField(verbose_name=u'是否为默认模块', default=False)

    language = models.CharField(verbose_name=u'编程语言', max_length=32)
    source_init_template = models.CharField(verbose_name=u'初始化模板类型', max_length=32)
    source_origin = models.SmallIntegerField(verbose_name=u'源码来源', null=True)
    source_type = models.CharField(verbose_name=u'源码托管类型', max_length=16, null=True)
    source_repo_id = models.IntegerField(verbose_name=u'源码 ID', null=True)
    exposed_url_type = models.IntegerField(verbose_name='访问 URL 版本', null=True)
    user_preferred_root_domain = models.CharField(max_length=255, verbose_name="用户偏好的根域名", null=True)
    runtime_type = models.CharField(max_length=32, verbose_name="运行时类型", default=RuntimeType.BUILDPACK)

    last_deployed_date = models.DateTimeField(verbose_name=u'最近部署时间', null=True)  # 范围：模块下的所有环境
    creator = BkUserField(null=True)

    class Meta:
        unique_together = ('application', 'name')

    @property
    def has_deployed(self) -> bool:
        """If current module has been SUCCESSFULLY deployed"""
        return bool(self.last_deployed_date)

    def get_source_obj(self) -> 'RepositoryInstance':
        """获取 Module 对应的源码 Repo 对象"""
        names = get_sourcectl_names()
        from paasng.platform.modules.specs import ModuleSpecs

        if names.validate_svn(self.source_type):
            from paasng.dev_resources.sourcectl.models import SvnRepository

            return SvnRepository.objects.get(pk=self.source_repo_id)
        elif names.validate_git(self.source_type):
            from paasng.dev_resources.sourcectl.models import GitRepository

            return GitRepository.objects.get(pk=self.source_repo_id)
        elif self.get_source_origin() in [SourceOrigin.IMAGE_REGISTRY]:
            from paasng.dev_resources.sourcectl.models import DockerRepository

            return DockerRepository.objects.get(pk=self.source_repo_id)
        elif ModuleSpecs(self).deploy_via_package:
            from paasng.dev_resources.sourcectl.models import SourcePackageRepository

            return SourcePackageRepository(self)

        # NOTE: 2020.08.19. 调整中, 目前这里不能保证必然有返回值
        logger.warning("Can't get source obj from %s", self)
        return None  # type: ignore

    def get_source_origin(self) -> SourceOrigin:
        return SourceOrigin(self.source_origin or SourceOrigin.AUTHORIZED_VCS)

    def get_envs(self, environment=None):
        if environment:
            return self.envs.get(environment=environment)
        return self.envs.all()

    def get_deploy_config(self):
        from .deploy_config import DeployConfig

        deploy_config, _ = DeployConfig.objects.get_or_create(module=self)
        return deploy_config

    def __str__(self):
        return f"{self.application.code}-{self.name}"
