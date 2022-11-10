# -*- coding: utf-8 -*-
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import models

from paas_wl.platform.applications.models import Release
from paas_wl.resources.utils.app import get_scheduler_client_by_app

if TYPE_CHECKING:
    from paas_wl.platform.applications.models.app import App


logger = logging.getLogger(__name__)


@dataclass
class AppDeletion:
    app: 'App'

    def perform(self, *args, **kwargs):
        """delete app resource under namespace"""
        try:
            release = Release.objects.get_latest(self.app, ignore_failed=True)
        except models.ObjectDoesNotExist:
            # 应用未发布过, 不执行删除逻辑
            return

        if release.build is None:
            # NOTE: 由于历史原因, 如果应用未发布过, 有可能存在 build is None 的 Release 对象。
            # 应用未发布过, 不执行删除逻辑
            return

        scheduler_client = get_scheduler_client_by_app(self.app)
        scheduler_client.delete_all_under_namespace(namespace=self.app.namespace)
        return
