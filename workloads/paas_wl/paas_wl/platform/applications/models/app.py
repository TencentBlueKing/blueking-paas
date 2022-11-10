# -*- coding: utf-8 -*-
import logging
from typing import Dict

from django.db import models
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
        return self.scheduler_safe_name

    @property
    def latest_config(self):
        return self.config_set.latest()

    def save(self, *args, **kwargs):
        """Override default save method"""
        app = super(App, self).save(*args, **kwargs)

        # Create necessary resources
        self.ensure_config()
        return app

    def ensure_config(self):
        """Create initial Config"""
        # Create config if not config can be found
        try:
            self.config_set.latest()
        except Config.DoesNotExist:
            Config.objects.create(app=self, owner=self.owner, runtime={})

    def get_structure(self) -> Dict:
        """This function provide compatibility with the field `App.structure`"""
        from paas_wl.workloads.processes.models import ProcessSpec

        return {item.name: item.computed_replicas for item in ProcessSpec.objects.filter(engine_app_id=self.uuid)}

    def __str__(self) -> str:
        return f'<{self.name}, region: {self.region}, type: {self.type}>'


# An alias name to distinguish from Platform's App(Application/BluekingApplication) model
EngineApp = App
