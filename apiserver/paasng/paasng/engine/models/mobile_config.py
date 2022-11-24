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
from django.conf import settings
from django.db import models
from rest_framework.serializers import SkipField

from paasng.engine.constants import LBPlans
from paasng.platform.applications.models import ModuleEnvironment
from paasng.utils.models import TimestampedModel


class MobileConfig(TimestampedModel):
    """Mobile config switcher for application"""

    environment = models.OneToOneField(
        'applications.ApplicationEnvironment',
        on_delete=models.CASCADE,
        related_name='mobile_config',
        db_constraint=False,
    )
    is_enabled = models.BooleanField(u'移动端配置是否生效', default=False)
    lb_plan = models.CharField(
        "load balancer plan",
        choices=LBPlans.get_choices(),
        max_length=64,
        default=LBPlans.LBDefaultPlan.value,
        help_text=u"which one-level load balancer plan the domain use",
    )
    access_url = models.URLField("移动端访问地址", blank=True, null=True, default='')

    def __str__(self):
        if self.is_enabled:
            return f"{self.environment}:{self.access_domain}"
        else:
            return f"{self.environment}:功能未开启"

    @property
    def access_domain(self):
        if self.is_enabled:
            # 如果应用填写了移动端访问地址，则使用用户填写的
            if self.access_url:
                return self.access_url

            # 没有填写移动端地址，则由平台按规则拼接
            return '{domain}/{region}-bkapp-{app_code}-{environment}/weixin/'.format(
                domain=settings.BKPAAS_WEIXIN_URL_MAP[self.environment.environment],
                region=self.environment.application.region,
                app_code=self.environment.application.code,
                environment=self.environment.environment,
            )
        raise SkipField(u"功能未开启")


def get_mobile_config(env: ModuleEnvironment) -> MobileConfig:
    """Get MobileConfig object by environment object, will auto create object"""
    return MobileConfig.objects.get_or_create(environment=env)[0]
