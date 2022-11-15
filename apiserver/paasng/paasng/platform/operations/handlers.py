# -*- coding: utf-8 -*-
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
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from paasng.engine.constants import JobStatus, OperationTypes
from paasng.engine.models import Deployment, ModuleEnvironmentOperations
from paasng.engine.signals import post_appenv_deploy
from paasng.platform.applications.models import Application, ApplicationEnvironment
from paasng.platform.applications.signals import (
    module_environment_offline_event,
    module_environment_offline_success,
    online_market_success,
    pre_delete_application,
    pre_delete_module,
)
from paasng.platform.modules.models import Module
from paasng.platform.operations.constant import OperationType
from paasng.platform.operations.models import (
    AppDeploymentOperationObj,
    ApplicationLatestOp,
    AppOfflineOperationObj,
    Operation,
)
from paasng.publish.market.constant import AppState
from paasng.publish.market.signals import offline_market, product_create_or_update_by_operator, release_to_market

logger = logging.getLogger(__name__)


@receiver(post_save)
def on_model_post_save(sender, instance, created, raw, using, update_fields, *args, **kwargs):
    """创建PAAS应用完成"""
    if isinstance(instance, Application) and created:
        # 由于application的id是uuid类型，另外application对象就是源对象，最终不记录source_object_id字段
        Operation.objects.create(
            application=instance,
            type=OperationType.CREATE_APPLICATION.value,
            user=instance.owner,
            region=instance.region,
        )
    elif isinstance(instance, Module) and created:
        Operation.objects.create(
            region=instance.region,
            application=instance.application,
            type=OperationType.CREATE_MODULE.value,
            user=instance.creator,
            module_name=instance.name,
        )
    elif isinstance(instance, Deployment) and not created:
        if instance.status == JobStatus.SUCCESSFUL.value and instance.app_environment.environment == "prod":
            application = instance.app_environment.application
            product = application.get_product()

            if product is None:
                return

            # 迁移未完成前的应用正式上线不会上线到桌面
            # Only do this check when "mgrlegacy" APP is enabled
            if (
                hasattr(application, "migrationprocess_set")
                and application.migrationprocess_set.exists()
                and application.migrationprocess_set.last().is_active()
            ):
                return

            if product.state != AppState.RELEASED.value:
                online_market_success.send(sender=instance, deployment_instance=instance)


@receiver(online_market_success)
def on_online_market_success(sender, deployment_instance, **kwargs):
    Operation.objects.filter(source_object_id=deployment_instance.id.hex).update(is_hidden=True)
    Operation.objects.create(
        application=deployment_instance.app_environment.application,
        type=OperationType.REGISTER_PRODUCT.value,
        user=deployment_instance.operator,
        source_object_id=deployment_instance.id.hex,
        # 只有默认模块才能上线到市场
        module_name=deployment_instance.app_environment.application.get_default_module().name,
    )


@receiver(product_create_or_update_by_operator)
def record_product_change_operation_log(sender, product, operator, created, **kwargs):
    """记录应用市场配置修改."""
    Operation.objects.create(
        application=product.application,
        type=OperationType.MODIFY_PRODUCT_ATTRIBUTES.value,
        user=operator,
        region=product.region,
        source_object_id=product.id,
        # 只有默认模块才能上线到市场
        module_name=product.application.get_default_module().name,
    )


@receiver(pre_delete_application)
def pre_delete_application_audit(sender, application: Application, operator: str, **kwargs):
    Operation.objects.create(
        application=application,
        type=OperationType.DELETE_APPLICATION.value,
        user=operator,
        region=application.region,
        source_object_id=application.id.hex,
    )


@receiver(pre_delete_module)
def pre_delete_module_audit(sender, module: Module, operator: str, **kwargs):
    Operation.objects.create(
        application=module.application,
        type=OperationType.DELETE_MODULE.value,
        user=operator,
        region=module.region,
        module_name=module.name,
        source_object_id=module.id.hex,
    )


@receiver(offline_market)
def on_offline_market(sender, application, operator, **kwargs):
    Operation.objects.create(
        application=application,
        type=OperationType.OFFLINE_MARKET.value,
        user=operator,
        region=application.region,
        source_object_id=application.id.hex,
        module_name=application.get_default_module().name,
    )


@receiver(release_to_market)
def on_release_market(sender, application, operator, **kwargs):
    Operation.objects.create(
        application=application,
        type=OperationType.RELEASE_TO_MARKET.value,
        user=operator,
        region=application.region,
        source_object_id=application.id.hex,
        module_name=application.get_default_module().name,
    )


@receiver(module_environment_offline_success)
def on_offline_success(sender, offline_instance, environment, **kwargs):
    AppOfflineOperationObj.update_operation(offline_instance)


@receiver(module_environment_offline_event)
def on_offline(sender, offline_instance, environment, **kwargs):
    AppOfflineOperationObj.create_operation(offline_instance)
    ModuleEnvironmentOperations.objects.create(
        operator=offline_instance.operator,
        app_environment=offline_instance.app_environment,
        application=offline_instance.app_environment.application,
        operation_type=OperationTypes.OFFLINE.value,
        object_uid=offline_instance.pk,
    )


@receiver(post_appenv_deploy)
def on_deploy_finished(sender: ApplicationEnvironment, deployment: Deployment, **kwargs):
    """Create new operation record when a deployment has finished"""
    AppDeploymentOperationObj.create_operation_from_deployment(deployment)


@receiver(post_save)
def on_operation_created(sender, instance, created, raw, using, update_fields, *args, **kwargs):
    """When an operation object was created, we should also update the application's
    corrensponding ApplicationLatestOp object.
    """
    if not (isinstance(instance, Operation) and created):
        return

    ApplicationLatestOp.objects.update_or_create(
        application=instance.application,
        defaults={
            'operation_type': instance.type,
            'operation_id': instance.id,
            'latest_operated_at': instance.created,
        },
    )
