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

from django.utils.translation import ugettext_lazy as _

from paasng.platform.engine.constants import AppEnvName
from paasng.platform.engine.models.config_var import ConfigVar
from paasng.platform.mgrlegacy.app_migrations.service import BaseRemoteServiceMigration

logger = logging.getLogger(__name__)


class RabbitMQServiceMigration(BaseRemoteServiceMigration):
    """RabbitMQ 增强服务迁移

    逻辑介绍:
    - 不迁移 rabbitmq 实例, 而采用从远端创建新的增强服务实例
    - 创建兼容的 v2 的环境变量 BK_BROKER_URL
    """

    service_name = "rabbitmq"

    def get_description(self):
        return "申请 RabbitMQ 服务实例"

    def migrate(self):
        module = self.context.app.get_default_module()
        service_obj = self.get_service()
        # 默认模块启用增强服务
        self.bind_service_to_default_module()

        # 绑定默认的 plan
        self.bind_default_plan_as_fallback()

        for environment in list(AppEnvName):
            env = module.get_envs(environment)
            engine_app = env.get_engine_app()
            rel = next(self.service_mgr.list_unprovisioned_rels(engine_app, service=service_obj), None)
            if rel is None:
                continue

            # 申请增强服务实例
            self.add_log(_(f"正在为 {environment} 环境创建 RabbitMQ 服务实例..."))
            rel.provision()

            instance = rel.get_instance()
            bk_broker_url = (
                "amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}".format(
                    **instance.credentials
                )
            )

            # 绑定环境变量
            ConfigVar.objects.create(
                module=module,
                environment=env,
                key="BK_BROKER_URL",
                value=bk_broker_url,
                description="RabbitMQ 服务迁移变量",
            )
            ConfigVar.objects.create(
                module=module, environment=env, key="IS_USE_CELERY", value="true", description="RabbitMQ 服务迁移变量"
            )
            if self.context.legacy_app_proxy.is_celery_beat_enabled():
                ConfigVar.objects.create(
                    module=module,
                    environment=env,
                    key="IS_USE_CELERY_BEAT",
                    value="true",
                    description="RabbitMQ 服务迁移变量",
                )

    def rollback_service_instance(self, environment: AppEnvName):
        """删除增强服务实例, 并释放远端资源"""
        engine_app_attachment = self.get_engine_app_attachment(environment=environment)
        self.add_log(f"即将解绑增强服务实例<{engine_app_attachment.service_instance_id}>")
        engine_app_attachment.delete()

    def should_skip(self):
        return not any(
            [self.context.legacy_app_proxy.is_celery_enabled(), self.context.legacy_app_proxy.is_celery_beat_enabled()]
        )

    def get_default_service_instance_info(self):
        """返回空值以创建新实例"""
        return None, None

    def get_stag_service_instance_info(self):
        return self.get_default_service_instance_info()

    def get_prod_service_instance_info(self):
        return self.get_default_service_instance_info()
