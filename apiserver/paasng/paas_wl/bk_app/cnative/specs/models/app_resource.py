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

import yaml
from django.db import models
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError as PDValidationError
from rest_framework.exceptions import ValidationError

from paas_wl.bk_app.applications.relationship import ModuleAttrFromID, ModuleEnvAttrFromName
from paas_wl.bk_app.cnative.specs.constants import DEFAULT_PROCESS_NAME, ApiVersion, DeployStatus
from paas_wl.bk_app.cnative.specs.crd.bk_app import (
    BkAppBuildConfig,
    BkAppProcess,
    BkAppResource,
    BkAppSpec,
    ObjectMetadata,
)
from paas_wl.core.env import EnvIsRunningHub
from paas_wl.core.resource import generate_bkapp_name
from paas_wl.utils.basic import to_error_string
from paas_wl.utils.models import BkUserField, TimestampedModel
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.models import Module


class AppModelResourceManager(models.Manager):
    """A custom manager for `AppModelResource`, provides useful utility functions"""

    def get_json(self, application: Application, module: Module) -> Dict:
        """Get the JSON value of app model resource by application"""
        return AppModelResource.objects.get(application_id=application.id, module_id=module.id).revision.json_value

    def create_from_resource(self, region: str, application_id: str, module_id: str, resource: "BkAppResource"):
        """Create a model resource object from `BkAppResource` object

        :param region: Application region
        :param application_id: ID of bk application object
        :param module_id: ID of Module object
        :param resource: `BkAppResource` object
        """
        json_value = resource.to_deployable()
        revision = AppModelRevision.objects.create(
            region=region,
            application_id=application_id,
            module_id=module_id,
            version=resource.apiVersion,
            json_value=json_value,
            yaml_value=yaml.dump(json_value, allow_unicode=True, default_flow_style=False),
        )
        model_resource = AppModelResource.objects.create(
            region=region, application_id=application_id, module_id=module_id, revision=revision
        )
        return model_resource

    def get_or_create_by_module(self, module: Module) -> "AppModelResource":
        try:
            return self.get(module_id=module.id)
        except AppModelResource.DoesNotExist:
            # 原逻辑: 创建云原生应用的模块时, 会创建 AppModelResource 用于占位
            res_name = generate_bkapp_name(module)
            resource = create_app_resource(res_name, image="stub")
            return self.create_from_resource(module.region, module.application.id, module.id, resource)


class AppModelResource(TimestampedModel):
    """Cloud-native Application's Model Resource"""

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), unique=True, null=False)
    module = ModuleAttrFromID()
    revision = models.OneToOneField(verbose_name="当前 revision", to="AppModelRevision", on_delete=models.CASCADE)

    objects = AppModelResourceManager()

    class Meta:
        indexes = [models.Index(fields=["application_id", "module_id"])]

    def use_resource(self, resource: "BkAppResource"):
        """Let current `AppModelResource` use a new resource

        :param resource: `BkAppResource` object
        """
        json_value = resource.to_deployable()
        self.revision = AppModelRevision.objects.create(
            region=self.region,
            application_id=self.application_id,
            module_id=self.module_id,
            version=resource.apiVersion,
            json_value=json_value,
            yaml_value=yaml.dump(json_value, allow_unicode=True, default_flow_style=False),
        )
        self.save(update_fields=["revision"])


class AppModelRevision(TimestampedModel):
    """Revisions of cloud-native Application's Model Resource"""

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), null=False)
    module = ModuleAttrFromID()

    # data fields
    version = models.CharField(verbose_name=_("模型版本"), max_length=64)
    yaml_value = models.TextField(verbose_name=_("应用模型（YAML 格式）"))
    # `json_value` is a duplicate of `yaml_value`
    json_value = models.JSONField(verbose_name=_("应用模型（JSON 格式）"))

    # status fields
    deployed_value = models.JSONField(verbose_name=_("已部署的应用模型（JSON 格式）"), null=True)
    has_deployed = models.BooleanField(verbose_name=_("是否已部署"), default=False)
    is_draft = models.BooleanField(verbose_name=_("是否草稿"), default=False)
    is_deleted = models.BooleanField(verbose_name=_("是否已删除"), default=False)

    class Meta:
        indexes = [models.Index(fields=["application_id", "module_id"])]


class AppModelDeployQuerySet(models.QuerySet):
    """Custom QuerySet for AppModelDeploy"""

    def filter_by_env(self, env: ModuleEnvironment):
        """Get all deploys under an env"""
        return self.filter(
            application_id=env.application_id,
            module_id=env.module_id,
            environment_name=env.environment,
        )

    def filter_succeeded(self):
        """return a queryset filter by status=READY"""
        return self.filter(status=DeployStatus.READY)

    def latest_succeeded(self):
        """Return the latest succeeded deployment of queryset"""
        return self.filter_succeeded().latest("created")

    def any_successful(self, env: ModuleEnvironment) -> bool:
        """Check if there are any successful deploys in given env"""
        return self.filter_by_env(env).filter_succeeded().exists()


class AppModelDeploy(TimestampedModel):
    """This model stores the cloud-native app's deployment histories.

    TODO: Add wl_app field so we can operate this model using wl_app directly
    instead of the combination of (application_id, module_id, environment_name).
    """

    application_id = models.UUIDField(verbose_name=_("所属应用"), null=False)
    module_id = models.UUIDField(verbose_name=_("所属模块"), null=False)
    module = ModuleAttrFromID()
    environment_name = models.CharField(
        verbose_name=_("环境名称"), choices=AppEnvName.get_choices(), null=False, max_length=16
    )
    environment = ModuleEnvAttrFromName()

    name = models.CharField(verbose_name=_("Deploy 名称"), max_length=64)
    revision = models.ForeignKey(to="AppModelRevision", on_delete=models.CASCADE)

    # The status and related fields are a brief abstraction of BkApp's status and "status.conditions".
    status = models.CharField(
        verbose_name=_("状态"), choices=DeployStatus.get_choices(), max_length=32, null=True, blank=True
    )
    reason = models.CharField(verbose_name=_("状态原因"), max_length=128, null=True, blank=True)
    message = models.TextField(verbose_name=_("状态描述文字"), null=True, blank=True)
    last_transition_time = models.DateTimeField(verbose_name=_("状态最近变更时间"), null=True)

    operator = BkUserField(verbose_name=_("操作者"))

    objects = AppModelDeployQuerySet.as_manager()

    class Meta:
        unique_together = ("application_id", "module_id", "environment_name", "name")

    def has_succeeded(self):
        return self.status == DeployStatus.READY

    @property
    def bk_app_resource(self) -> BkAppResource:
        """Get the BkAppResource object of the current revision"""
        return BkAppResource(**self.revision.json_value)


def create_app_resource(
    name: str,
    image: str,
    api_version: Optional[str] = ApiVersion.V1ALPHA2,
    command: Optional[List[str]] = None,
    args: Optional[List[str]] = None,
    target_port: Optional[int] = None,
) -> BkAppResource:
    """Create a new BkApp Resource with simple parameters

    :param name: Resource name
    :returns: `BkAppResource` object
    """
    obj = BkAppResource(
        apiVersion=api_version,
        metadata=ObjectMetadata(name=name),
        spec=BkAppSpec(
            build=BkAppBuildConfig(
                image=image,
            ),
            processes=[
                BkAppProcess(
                    name=DEFAULT_PROCESS_NAME,
                    command=command or [],
                    args=args or [],
                    targetPort=target_port or None,
                )
            ],
        ),
    )
    # 兼容 v1alpha1 版本逻辑
    if api_version == ApiVersion.V1ALPHA1:
        obj.spec.build = None
        obj.spec.processes[0].image = image

    return obj


def update_app_resource(app: Application, module: Module, payload: Dict):
    """Update application's resource

    :param payload: application model resource JSON
    :raise: `ValidationError` when payload is invalid
    :raise: `ValueError` if model resource has not been initialized for given application
    """
    # force replace metadata.name with app_code to avoid user modify
    payload["metadata"]["name"] = generate_bkapp_name(module)

    try:
        obj = BkAppResource(**payload)
    except PDValidationError as e:
        raise ValidationError(to_error_string(e))

    # Get current resource payload
    try:
        # Only the default module is supported currently, so `module_id` is ignored in query
        # conditions.
        model_resource = AppModelResource.objects.get(application_id=app.id, module_id=module.id)
    except AppModelResource.DoesNotExist:
        raise ValueError(f"{app.id} not initialized")

    model_resource.use_resource(obj)


# Register env_is_running implementations
def _get_env_is_running(env):
    """Get "is_running" status by querying for successful deploys."""
    return AppModelDeploy.objects.any_successful(env) and not env.is_offlined


EnvIsRunningHub.register_func(ApplicationType.CLOUD_NATIVE, _get_env_is_running)
