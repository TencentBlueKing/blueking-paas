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
import json
import logging
from typing import Dict, List, Optional

import yaml
from django.db import models
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError as PDValidationError
from pydantic.error_wrappers import display_errors
from rest_framework.exceptions import ValidationError

from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.applications.relationship import ModuleAttrFromID, ModuleEnvAttrFromName
from paas_wl.utils.models import BkUserField, TimestampedModel
from paas_wl.workloads.images.models import AppImageCredential, ImageCredentialRef
from paasng.dev_resources.servicehub.manager import mixed_service_mgr
from paasng.platform.applications.models import Application, ModuleEnvironment

from .configurations import generate_builtin_configurations, merge_envvars
from .constants import (
    ACCESS_CONTROL_ANNO_KEY,
    BKAPP_CODE_ANNO_KEY,
    BKAPP_NAME_ANNO_KEY,
    BKAPP_REGION_ANNO_KEY,
    BKPAAS_ADDONS_ANNO_KEY,
    BKPAAS_DEPLOY_ID_ANNO_KEY,
    BKPAAS_RESERVED_ANNO_PREFIX,
    DEFAULT_PROCESS_NAME,
    ENVIRONMENT_ANNO_KEY,
    IMAGE_CREDENTIALS_REF_ANNO_KEY,
    MODULE_NAME_ANNO_KEY,
    AppEnvName,
    DeployStatus,
)
from .v1alpha1.bk_app import BkAppProcess, BkAppResource, BkAppSpec, ObjectMetadata

logger = logging.getLogger(__name__)


class AppModelResourceManager(models.Manager):
    """A custom manager for `AppModelResource`, provides useful utility functions"""

    def get_json(self, application: Application) -> Dict:
        """Get the JSON value of app model resource by application"""
        return AppModelResource.objects.get(application_id=application.id).revision.json_value

    def create_from_resource(self, region: str, application_id: str, module_id: str, resource: 'BkAppResource'):
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


class AppModelResource(TimestampedModel):
    """Cloud-native Application's Model Resource"""

    application_id = models.UUIDField(verbose_name=_('所属应用'), null=False)
    module_id = models.UUIDField(verbose_name=_('所属模块'), unique=True, null=False)
    module = ModuleAttrFromID()
    revision = models.OneToOneField(verbose_name='当前 revision', to='AppModelRevision', on_delete=models.CASCADE)

    objects = AppModelResourceManager()

    class Meta:
        indexes = [models.Index(fields=['application_id', 'module_id'])]

    def use_resource(self, resource: 'BkAppResource'):
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
        self.save(update_fields=['revision'])


class AppModelRevision(TimestampedModel):
    """Revisions of cloud-native Application's Model Resource"""

    application_id = models.UUIDField(verbose_name=_('所属应用'), null=False)
    module_id = models.UUIDField(verbose_name=_('所属模块'), null=False)
    module = ModuleAttrFromID()

    # data fields
    version = models.CharField(verbose_name=_('模型版本'), max_length=64)
    yaml_value = models.TextField(verbose_name=_('应用模型（YAML 格式）'))
    # `json_value` is a duplication with `yaml_value`
    json_value = models.JSONField(verbose_name=_('应用模型（JSON 格式）'))

    # status fields
    has_deployed = models.BooleanField(verbose_name=_('是否已部署'), default=False)
    is_draft = models.BooleanField(verbose_name=_('是否草稿'), default=False)
    is_deleted = models.BooleanField(verbose_name=_('是否已删除'), default=False)

    class Meta:
        indexes = [models.Index(fields=['application_id', 'module_id'])]


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
        return self.filter_succeeded().latest('created')

    def any_successful(self, env: ModuleEnvironment) -> bool:
        """Check if there are any successful deploys in given env"""
        return self.filter_by_env(env).filter_succeeded().exists()


class AppModelDeploy(TimestampedModel):
    """Cloud-native App's deployments

    TODO: Add wl_app field so we can operate this model using wl_app directly
    instead of the combination of (application_id, module_id, environment_name).
    """

    application_id = models.UUIDField(verbose_name=_('所属应用'), null=False)
    module_id = models.UUIDField(verbose_name=_('所属模块'), null=False)
    module = ModuleAttrFromID()
    environment_name = models.CharField(
        verbose_name=_('环境名称'), choices=AppEnvName.get_choices(), null=False, max_length=16
    )
    environment = ModuleEnvAttrFromName()

    name = models.CharField(verbose_name=_('Deploy 名称'), max_length=32)
    revision = models.ForeignKey(to='AppModelRevision', on_delete=models.CASCADE)

    # The status and related fields are a brief abstraction of BkApp's status and "status.conditions".
    status = models.CharField(
        verbose_name=_('状态'), choices=DeployStatus.get_choices(), max_length=32, null=True, blank=True
    )
    reason = models.CharField(verbose_name=_('状态原因'), max_length=128, null=True, blank=True)
    message = models.TextField(verbose_name=_('状态描述文字'), null=True, blank=True)
    last_transition_time = models.DateTimeField(verbose_name=_('状态最近变更时间'), null=True)

    operator = BkUserField(verbose_name=_('操作者'))

    objects = AppModelDeployQuerySet.as_manager()

    class Meta:
        unique_together = ('application_id', 'module_id', 'environment_name', 'name')

    def build_manifest(self, env: ModuleEnvironment, credential_refs: List[ImageCredentialRef]):
        """inject bkpaas-specific properties to annotations

        :param env: ModuleEnv object
        :param credential_refs: Image credential ref objects
        """
        wl_app = WlApp.objects.get(pk=env.engine_app_id)
        manifest = BkAppResource(**self.revision.json_value)

        # 更新注解，包含应用基本信息，增强服务，访问控制，镜像凭证等
        self._inject_annotations(manifest, env.application, env, wl_app, credential_refs)

        # 注入平台内置环境变量
        manifest.spec.configuration.env = merge_envvars(
            manifest.spec.configuration.env, generate_builtin_configurations(env=env)
        )

        data = manifest.dict()
        # refresh status.conditions
        data["status"] = {"conditions": []}
        return data

    def _inject_annotations(
        self,
        manifest: BkAppResource,
        application: Application,
        env: ModuleEnvironment,
        wl_app: WlApp,
        credential_refs: List[ImageCredentialRef],
    ) -> None:
        # 检查 annotations 中的各个值，如果占用 paas 保留的前缀，则 pop 掉
        for key in manifest.metadata.annotations:
            if key.startswith(BKPAAS_RESERVED_ANNO_PREFIX):
                manifest.metadata.annotations.pop(key)

        # inject bkapp deploy info
        manifest.metadata.annotations[BKPAAS_DEPLOY_ID_ANNO_KEY] = str(self.pk)

        # inject bkapp basic info
        manifest.metadata.annotations.update(
            {
                BKAPP_REGION_ANNO_KEY: application.region,
                BKAPP_NAME_ANNO_KEY: application.name,
                BKAPP_CODE_ANNO_KEY: application.code,
                MODULE_NAME_ANNO_KEY: env.module.name,
                ENVIRONMENT_ANNO_KEY: env.environment,
            }
        )

        # inject addons services
        manifest.metadata.annotations[BKPAAS_ADDONS_ANNO_KEY] = json.dumps(
            [svc.name for svc in mixed_service_mgr.list_binded(env.module)]
        )

        # flush credentials and inject a flag to tell operator that workloads have crated the secret
        if credential_refs:
            AppImageCredential.objects.flush_from_refs(
                application=application, wl_app=wl_app, references=credential_refs
            )
            manifest.metadata.annotations[IMAGE_CREDENTIALS_REF_ANNO_KEY] = "true"
        else:
            manifest.metadata.annotations[IMAGE_CREDENTIALS_REF_ANNO_KEY] = ""

        # inject access control enable info
        try:
            from paasng.security.access_control.models import ApplicationAccessControlSwitch
        except ImportError:
            logger.info('access control only supported in te region, skip when inject annotations...')
        else:
            if ApplicationAccessControlSwitch.objects.is_enabled(application):
                manifest.metadata.annotations[ACCESS_CONTROL_ANNO_KEY] = "true"


def create_app_resource(
    name: str,
    image: str,
    command: Optional[List[str]] = None,
    args: Optional[List[str]] = None,
    target_port: Optional[int] = None,
) -> BkAppResource:
    """Create a new BkApp Resource with simple parameters

    :param name: Resource name
    :returns: `BkAppResource` object
    """
    obj = BkAppResource(
        metadata=ObjectMetadata(name=name),
        spec=BkAppSpec(
            processes=[
                BkAppProcess(
                    name=DEFAULT_PROCESS_NAME,
                    image=image,
                    command=command or [],
                    args=args or [],
                    targetPort=target_port or None,
                )
            ]
        ),
    )
    # TODO: Allow the default fields to be skipped, such as empty "command" and "args"
    return obj


def update_app_resource(app: Application, payload: Dict):
    """Update application's resource

    :param payload: application model resource JSON
    :raise: `ValidationError` when payload is invalid
    :raise: `ValueError` if model resource has not been initialized for given application
    """
    # force replace metadata.name with app_code to avoid user modify
    payload['metadata']['name'] = app.code

    try:
        obj = BkAppResource(**payload)
    except PDValidationError as e:
        raise ValidationError(to_error_string(e))

    # Get current resource payload
    try:
        # Only the default module is supported currently, so `module_id` is ignored in query
        # conditions.
        model_resource = AppModelResource.objects.get(application_id=app.id)
    except AppModelResource.DoesNotExist:
        raise ValueError(f'{app.id} not initialized')

    model_resource.use_resource(obj)


def to_error_string(exc: PDValidationError) -> str:
    """Transform a pydantic Exception object to an one-line string"""
    # TODO: Improve error message format
    return display_errors(exc.errors()).replace('\n', ' ')


def default_bkapp_name(env: ModuleEnvironment) -> str:
    """Get name of the default BkApp resource by env.

    :param env: ModuleEnv object
    :return: BkApp resource name
    """
    # TODO: Should we add "environment" field to name? Result may exceeds the
    # max-length limit on the operator side.
    return f'{env.application.code}'
