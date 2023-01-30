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
from typing import Dict

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from jsonfield import JSONField

from paas_wl.platform.applications.constants import EngineAppType
from paas_wl.platform.applications.models import UuidAuditedModel
from paas_wl.platform.applications.models.config import Config
from paas_wl.platform.applications.models.validators import validate_app_name, validate_app_structure
from paas_wl.platform.applications.struct_models import ModuleEnv

logger = logging.getLogger(__name__)


class AppManager(models.Manager):
    """Custom manager for App(EngineApp) model"""

    def get_by_env(self, env: ModuleEnv) -> 'App':
        """Get an EngineApp by env object"""
        return self.get_queryset().get(pk=env.engine_app_id)


class App(UuidAuditedModel):
    """App Model"""

    owner = models.CharField(max_length=64)
    region = models.CharField(max_length=32)
    name = models.SlugField(max_length=64, validators=[validate_app_name])
    # deprecated field
    structure = JSONField(default={}, blank=True, validators=[validate_app_structure])
    type = models.CharField(verbose_name='应用类型', max_length=16, default=EngineAppType.DEFAULT.value, db_index=True)

    objects = AppManager()

    class Meta:
        unique_together = ('region', 'name')

    @property
    def scheduler_safe_name(self):
        """app name in scheduler backend"""
        return self.name.replace('_', '0us0')

    @property
    def scheduler_safe_name_with_region(self):
        return f"{self.region}-{self.scheduler_safe_name}"

    @property
    def namespace(self):
        # Both default and cloud-native are using this method to get namespace
        # at this moment.
        return self.scheduler_safe_name

    @property
    def latest_config(self):
        return self.config_set.latest()

    def get_structure(self) -> Dict:
        """This function provide compatibility with the field `App.structure`"""
        from paas_wl.workloads.processes.models import ProcessSpec

        return {item.name: item.computed_replicas for item in ProcessSpec.objects.filter(engine_app_id=self.uuid)}

    def has_proc_type(self, proc_type: str) -> bool:
        """Check if current app has a process type, e.g. "web" """
        return proc_type in self.get_structure()

    def __str__(self) -> str:
        return f'<{self.name}, region: {self.region}, type: {self.type}>'


def get_ns(env: ModuleEnv) -> str:
    """Get namespace by env object, a shortcut function"""
    engine_app = EngineApp.objects.get_by_env(env)
    return engine_app.namespace


# An alias name to distinguish from Platform's App(Application/BluekingApplication) model
EngineApp = App


@receiver(post_save, sender=App)
def on_app_created(sender, instance, created, *args, **kwargs):
    """Do extra things when an app was created"""
    if created:
        create_initial_config(instance)


def create_initial_config(app: App):
    """Make sure the initial Config was created"""
    try:
        app.config_set.latest()
    except Config.DoesNotExist:
        Config.objects.create(app=app, owner=app.owner, runtime={})
