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
import uuid
from typing import ClassVar, Dict, Optional, Tuple, Type, Union

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext as _

from paasng.dev_resources.servicehub.constants import LEGACY_PLAN_ID, LEGACY_PLAN_INSTANCE
from paasng.dev_resources.servicehub.local.manager import LocalPlainInstanceMgr, LocalServiceObj
from paasng.dev_resources.servicehub.manager import LocalServiceMgr, RemoteServiceMgr, mixed_service_mgr
from paasng.dev_resources.servicehub.models import RemoteServiceEngineAppAttachment, ServiceEngineAppAttachment
from paasng.dev_resources.servicehub.remote.manager import RemotePlainInstanceMgr
from paasng.dev_resources.servicehub.remote.store import get_remote_store
from paasng.dev_resources.servicehub.services import PlainInstanceMgr
from paasng.dev_resources.services.models import Plan, ServiceInstance
from paasng.engine.constants import AppEnvName
from paasng.platform.mgrlegacy.app_migrations.base import BaseMigration

logger = logging.getLogger(__name__)
local_service_mgr = LocalServiceMgr()
remote_service_mgr = RemoteServiceMgr(get_remote_store())


class LegacyBaseServiceMigration(BaseMigration):
    # TODO: remove this class
    service_name: str = ''

    def get_service(self, service_name: str):
        return mixed_service_mgr.find_by_name(service_name, self.context.app.region)

    def _bind_service(self, service_name: str):
        service_obj = self.get_service(service_name)

        # Only local service can be migrated because remote services does not support remote
        # instance data written at this moment.
        if not isinstance(service_obj, LocalServiceObj):
            if service_name in ['rabbitmq']:
                # 远程增强服务是重新申请新实例, 无法进行数据同步
                logger.warning(f"support {service_name} to migrate")
            else:
                raise RuntimeError(f'service {service_name} is not local service, will abort')

        module = self.context.app.get_default_module()
        mixed_service_mgr.bind_service(service_obj, module)

    def _get_environment_attachment(self, environment: str):
        try:
            service_attachment = self.context.app.envs.get(environment=environment).engine_app.service_attachment.get(
                service__name=self.service_name
            )
            return service_attachment
        except ObjectDoesNotExist:
            logger.debug("service_attachment for application:%s not exists!" % self.context.app.code)

    def _add_service_instance(self, environment: str, credentials: Dict, config: Optional[Dict] = None):
        service_attachment = self._get_environment_attachment(environment=environment)
        kwargs = {
            "plan": service_attachment.plan,
            "service": service_attachment.service,
            "credentials": json.dumps(credentials),
        }
        if config is not None:
            kwargs["config"] = json.dumps(config)

        if not service_attachment.service_instance:
            service_instance = ServiceInstance.objects.create(**kwargs)
            service_attachment.service_instance = service_instance
            service_attachment.save(update_fields=['service_instance'])

    def get_stag_service_data(self):
        raise NotImplementedError

    def get_prod_service_data(self):
        raise NotImplementedError

    def get_service_data(self, environment):
        if environment == 'stag':
            return self.get_stag_service_data()
        elif environment == 'prod':
            return self.get_prod_service_data()
        else:
            raise ValueError(environment)

    def migrate(self):
        # get instantiate
        instance_info = []
        for environment in AppEnvName:
            credentials, config = self.get_service_data(environment)
            if credentials is None:
                continue

            kwargs = dict(environment=environment, credentials=credentials)
            if config is not None:
                kwargs['config'] = config
            instance_info.append(kwargs)

        # bind only when necessary
        if instance_info:
            self._bind_service(self.service_name)

        # add not empty instance
        for kwargs in instance_info:
            self._add_service_instance(**kwargs)

    def rollback(self):
        for environment in AppEnvName:
            service_attachment = self._get_environment_attachment(environment=environment)
            if service_attachment is None:
                continue

            service_instance = service_attachment.service_instance
            if service_instance is not None:
                service_attachment.service_instance = None
                service_attachment.save(update_fields=['service_instance'])
                ServiceInstance.objects.filter(pk=service_instance.pk).delete()

            try:
                self.context.app.envs.get(environment=environment).engine_app.service_attachment.filter(
                    service__name=self.service_name
                ).delete()
            except ObjectDoesNotExist:
                logger.warning("service rollback delete service_attachment delete fail")

            self.context.app.serviceapplicationattachment_set.all().delete()


class BaseServiceMigration(BaseMigration):

    service_name: ClassVar[str] = ''
    service_mgr: Union[LocalServiceMgr, RemoteServiceMgr]
    engine_app_attachment_cls: Type[Union[ServiceEngineAppAttachment, RemoteServiceEngineAppAttachment]]

    def migrate(self):
        instance_info_list = []
        for environment in AppEnvName:
            credentials, config = self.get_service_instance_info(AppEnvName(environment))
            if credentials is not None:
                instance_info_list.append(
                    {"environment": AppEnvName(environment), "credentials": credentials, "config": config}
                )

        # 如果该增强服务无实例数据, 则不进行服务
        if not instance_info_list:
            self.add_log(_("跳过步骤: 绑定增强服务<{service_name}>").format(service_name=self.service_name))
            return

        # 默认模块启用增强服务
        self.bind_service_to_default_module()

        # 创建 engine_app_attachment
        for ins in instance_info_list:
            self.migrate_service_instance(**ins)  # type: ignore

        if len(instance_info_list) != len(list(AppEnvName)):
            self.bind_default_plan_as_fallback()

    def rollback(self):
        for environment in AppEnvName:
            self.rollback_service_instance(environment=AppEnvName(environment))

    def get_service(self):
        return self.service_mgr.find_by_name(self.service_name, self.context.app.region)

    def bind_service_to_default_module(self):
        """绑定增强服务至模块, 但不创建 engine_app 与 service 之间的绑定关系"""
        module = self.context.app.get_default_module()
        service_obj = self.get_service()
        self.add_log(
            _("绑定增强服务<{service_obj}>至默认模块<{module_name}>").format(
                service_obj=service_obj.name, module_name=module.name
            )
        )
        self.service_mgr.bind_service_partial(service_obj, module=module)

    def bind_default_plan_as_fallback(self):
        """为未实例化增强服务实例的环境绑定默认的 plan

        触发条件: 当且仅当当前应用在某一环境未部署过时, 才会触发该逻辑
        """
        module = self.context.app.get_default_module()
        service_obj = self.get_service()
        self.add_log(
            _("绑定增强服务<{service_obj}>的默认方案至默认模块<{module_name}>").format(
                service_obj=service_obj.name, module_name=module.name
            )
        )
        self.service_mgr.bind_service(service_obj, module=module)

    def migrate_service_instance(self, environment: AppEnvName, credentials: Dict, config: Optional[Dict] = None):
        """迁移增强服务实例信息至远程增强服务"""
        engine_app_attachment = self.get_engine_app_attachment(environment=environment)
        if not credentials:
            return

        mgr = self.get_instance_mgr(engine_app_attachment)
        if not mgr.is_provisioned():
            engine_app_attachment.plan_id = self.get_plan_uuid(environment=environment)
            engine_app_attachment.save(update_fields=["plan_id"])
            mgr.create(credentials=credentials, config=config or {})

    def rollback_service_instance(self, environment: AppEnvName):
        """从远程增强服务中回滚(删除)增强服务实例信息"""
        engine_app_attachment = self.get_engine_app_attachment(environment=environment)
        mgr = self.get_instance_mgr(engine_app_attachment)

        if mgr.is_provisioned():
            self.add_log(
                _("即将解绑增强服务实例<{service_instance_id}>").format(
                    service_instance_id=engine_app_attachment.service_instance_id
                )
            )
            mgr.destroy()
        else:
            # 仅删除绑定关系
            engine_app_attachment.delete()

    def get_engine_app_attachment(
        self, environment: AppEnvName
    ) -> Union[ServiceEngineAppAttachment, RemoteServiceEngineAppAttachment]:
        """Bind a service to engine_app, without binding any plan"""
        service_obj = self.get_service()
        engine_app = self.context.app.envs.get(environment=environment).engine_app
        service_attachment, _ = self.engine_app_attachment_cls.objects.get_or_create(
            engine_app=engine_app,
            service_id=service_obj.uuid,
            defaults=dict(plan_id=self.get_plan_uuid(environment=environment)),
        )
        return service_attachment

    def get_service_instance_info(self, environment: AppEnvName) -> Tuple[Dict, Dict]:
        """获取增强服务实例配置信息"""
        if environment == AppEnvName.STAG:
            return self.get_stag_service_instance_info()
        elif environment == AppEnvName.PROD:
            return self.get_prod_service_instance_info()
        else:
            raise ValueError(f"Unsupported environment: {environment}")

    def get_instance_mgr(
        self, engine_app_attachment: Union[RemoteServiceEngineAppAttachment, ServiceEngineAppAttachment]
    ) -> PlainInstanceMgr:
        raise NotImplementedError

    def get_stag_service_instance_info(self) -> Tuple[Dict, Dict]:
        raise NotImplementedError

    def get_prod_service_instance_info(self) -> Tuple[Dict, Dict]:
        raise NotImplementedError

    def get_plan_uuid(self, environment: AppEnvName) -> uuid.UUID:
        """获取迁移应用绑定的增强服务方案"""
        raise NotImplementedError


class BaseLocalServiceMigration(BaseServiceMigration):
    service_mgr = local_service_mgr
    engine_app_attachment_cls = ServiceEngineAppAttachment

    def get_plan_uuid(self, environment: AppEnvName) -> uuid.UUID:
        # 本地增强服务的绑定关系有外键约束, 必须用真实值。
        service_obj = self.get_service()
        plans = list(service_obj.get_plans(is_active=True) + service_obj.get_plans(is_active=False))
        if not plans:
            # 由于本地增强服务的绑定有外键约束, 因此在不存在 plan 可以关联时, 需要创建一个占位用的 plan
            logger.warning("无法绑定至合适的 plan")
            Plan.objects.get_or_create(
                uuid=LEGACY_PLAN_ID,
                service=service_obj.db_object,
                defaults=dict(
                    name=LEGACY_PLAN_INSTANCE["name"],
                    description=LEGACY_PLAN_INSTANCE["description"],
                ),
            )
            return LEGACY_PLAN_ID
        return plans[0].uuid

    def get_instance_mgr(self, engine_app_attachment: ServiceEngineAppAttachment):
        return LocalPlainInstanceMgr(engine_app_attachment)


class BaseRemoteServiceMigration(BaseServiceMigration):
    service_mgr = remote_service_mgr
    engine_app_attachment_cls = RemoteServiceEngineAppAttachment

    def get_plan_uuid(self, environment: AppEnvName) -> uuid.UUID:
        return LEGACY_PLAN_ID

    def get_instance_mgr(self, engine_app_attachment: RemoteServiceEngineAppAttachment):
        return RemotePlainInstanceMgr(engine_app_attachment, self.service_mgr)
