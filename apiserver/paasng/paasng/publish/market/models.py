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
import os
import time
from collections import namedtuple
from dataclasses import dataclass
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from jsonfield import JSONField
from pilkit.processors import ResizeToFill
from translated_fields import TranslatedFieldWithFallback

from paasng.platform.applications.models import Application
from paasng.platform.applications.specs import AppSpecs
from paasng.platform.core.storages.s3 import app_logo_storage
from paasng.platform.modules.models import Module
from paasng.publish.market import constant
from paasng.utils.models import OwnerTimestampedModel, ProcessedImageField, TimestampedModel, WithOwnerManager

logger = logging.getLogger(__name__)


class TagManager(models.Manager):
    def get_query_set(self):
        return super(TagManager, self).get_query_set().filter(region__in=[settings.RUN_VER, 'all'])

    def get_default_tag(self):
        """自动给应用创建市场信息时,使用默认分类"""
        # 将最后添加的分类设置为默认分类
        return self.last()


class Tag(models.Model):
    """
    按用途分类
    """

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"APP一级分类", help_text=u"对于一级分类，该字段为空"
    )  # 一级分类，则该字段可为空
    name = models.CharField(u"分类名称", max_length=64, help_text=u"分类名称")
    remark = models.CharField(u"备注", blank=True, null=True, max_length=255, help_text=u"备注")
    index = models.IntegerField(u"排序", default=0, help_text=u"显示排序字段")
    enabled = models.BooleanField(u"是否可选", default=True, help_text=u"创建应用时是否可选择该分类")
    region = models.CharField(u"部署环境", max_length=32, help_text=u"部署区域")

    objects = TagManager()

    class Meta(object):
        ordering = ('index', 'id')

    def get_name_display(self):
        if self.parent:
            return u"%s-%s" % (self.parent.name, self.name)
        else:
            return _(self.name)

    def __str__(self):
        return '{}:{} region={} parent={}'.format(self.id, self.name, self.region, self.parent)


class ProductManager(WithOwnerManager):
    def owned_and_collaborated_by(self, user):
        application_ids = Application.objects.filter_by_user(user).values_list("id", flat=True)
        return self.filter(application__id__in=application_ids)

    def create_default_product(self, application: Application) -> 'Product':
        product, created = self.get_or_create(
            application=application,
            code=application.code,
            logo=None,
            tag=Tag.objects.get_default_tag(),
            type=constant.AppType.PAAS_APP.value,
            defaults={
                "name_en": application.name,
                "name_zh_cn": application.name,
                "introduction_en": application.name,
                "introduction_zh_cn": application.name,
            },
        )
        if created:
            DisplayOptions.objects.create(product=product)
        return product


def upload_renamed_to_app_code(instance: 'Product', filename: str):
    """Generate uploaded logo filename"""
    name = filename

    path = os.path.split(name)[:-1]
    ext = os.path.splitext(name)[-1]
    name = "{code}_{ts}{ext}".format(code=instance.code, ts=int(time.time()), ext=ext)
    name = os.path.join(os.path.join(*path), name)
    return name


class Product(OwnerTimestampedModel):
    """蓝鲸应用: 开发者中心的编辑属性"""

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, verbose_name=u"PAAS 应用", blank=True, null=True, help_text=u"PAAS应用"
    )

    # 基本属性
    code = models.CharField(u'应用编码', max_length=64, unique=True, help_text=u"应用编码")
    name = TranslatedFieldWithFallback(
        models.CharField('应用在市场中的名称', max_length=64, help_text="目前与应用名称保持一致，在 2 个表中修改时都需要相互同步数据，不能超过20个字符")
    )
    logo = ProcessedImageField(
        storage=app_logo_storage,
        upload_to=upload_renamed_to_app_code,
        processors=[ResizeToFill(144, 144)],
        format='PNG',
        options={'quality': 95},
    )
    introduction = TranslatedFieldWithFallback(models.TextField("应用简介", help_text="应用简介"))
    description = TranslatedFieldWithFallback(models.TextField("应用描述", help_text="应用描述", default=""))
    tag = models.ForeignKey(
        Tag, verbose_name=u"app分类", blank=True, null=True, default=None, on_delete=models.SET_NULL, help_text=u"按用途分类"
    )  # 永远绑定到二级 tag
    type = models.SmallIntegerField(u"应用类型", choices=constant.AppType.get_choices(), help_text=u"按实现方式分类")
    state = models.SmallIntegerField(u"状态", choices=constant.AppState.get_choices(), default=1, help_text=u"应用状态")
    # 要为 “所属业务” 取一个抽象的字段名字很难，一个业务代表着应用的一类理想目标用户群体
    # 想了半天，取 related corpration product（相关联的公司产品）
    related_corp_products = JSONField(default=[], help_text='所属业务')
    # 可见范围
    visiable_labels = JSONField(u"可见范围标签", blank=True, null=True)

    objects = ProductManager()

    def get_contact(self):
        return self.displayoptions.contact

    def get_logo_url(self):
        # Read logo from application
        # TODO: Remove logo entirely from Product
        return self.application.get_logo_url()

    def transform_visiable_labels(self):
        """可见范围转为蓝鲸桌面中存储的格式
        >>> data = [
        ...     {
        ...         "id": 100,
        ...         "type": "department",
        ...         "name": "xx部门"
        ...     },
        ...     {
        ...         "id": 2001,
        ...         "type": "user",
        ...         "name": "user1"
        ...     }
        ... ]
        >>> Product(visiable_labels=data).transform_visiable_labels(data)
        ',u2001,d100,'
        """
        # 没有设置可见范围，则返回空字符串
        if not self.visiable_labels:
            return ""

        # 将结构化的数据转换为字符串",d100,d101,u2001,u2580,d110,"
        username_list = {"u:%s" % u.get("id") for u in self.visiable_labels if u.get("type") == "user"}
        department_list = {"d:%s" % d.get("id") for d in self.visiable_labels if d.get("type") == "department"}
        label_sets = set(username_list) | set(department_list)
        if not label_sets:
            return ""

        return "," + ",".join([str(label) for label in label_sets]) + ","


class DisplayOptions(models.Model):
    """app展示相关的属性"""

    product = models.OneToOneField(Product, on_delete=models.CASCADE)

    visible = models.BooleanField(u"是否显示在桌面", default=True, help_text=u"选项: true(是)，false(否)")

    width = models.IntegerField(u"app页面宽度", help_text=u"应用页面宽度，必须为整数，单位为px", default=890)
    height = models.IntegerField(u"app页面高度", help_text=u"应用页面高度，必须为整数，单位为px", default=550)

    is_win_maximize = models.BooleanField(u"是否默认窗口最大化", default=False)
    win_bars = models.BooleanField(u"窗口是否显示评分和介绍按钮", default=True, help_text=u"选项: true(on)，false(off)")
    resizable = models.BooleanField(u"是否能对窗口进行拉伸", default=True, help_text=u"选项：true(可以拉伸)，false(不可以拉伸)")

    # App 右下角展示联系人，以;分割
    contact = models.CharField(u"联系人", null=True, blank=True, max_length=128)
    open_mode = models.CharField(
        "打开方式", max_length=20, choices=constant.OpenMode.get_django_choices(), default=constant.OpenMode.NEW_TAB.value
    )


class MarketConfigManager(models.Manager):
    def get_or_create_by_app(self, application: Application) -> Tuple['MarketConfig', bool]:
        """Get or create a MarketConfig object by application"""
        try:
            return application.market_config, False
        except MarketConfig.DoesNotExist:
            enabled = False
            url_type = constant.ProductSourceUrlType.DISABLED.value
            if application.engine_enabled:
                url_type = constant.ProductSourceUrlType.ENGINE_PROD_ENV.value
                product = application.get_product()
                if product and product.state == constant.AppState.RELEASED.value:
                    enabled = True

            confirm_required_when_publish = AppSpecs(application).confirm_required_when_publish
            obj = MarketConfig.objects.create(
                application=application,
                enabled=enabled,
                auto_enable_when_deploy=not confirm_required_when_publish,
                source_module=application.get_default_module(),
                source_url_type=url_type,
            )
            return obj, True

    def update_enabled(self, application: Application, status: bool) -> 'MarketConfig':
        obj, _ = self.get_or_create_by_app(application)
        obj.enabled = status
        obj.save(update_fields=['enabled'])
        return obj

    def enable_app(self, application: Application):
        self.update_enabled(application, True)

    def disable_app(self, application: Application):
        self.update_enabled(application, False)


class MarketConfig(TimestampedModel):
    """应用市场相关功能配置"""

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, verbose_name="蓝鲸应用", related_name='market_config'
    )
    enabled = models.BooleanField(verbose_name='是否开启')
    auto_enable_when_deploy = models.BooleanField(null=True, verbose_name="成功部署主模块正式环境后, 是否自动打开市场")
    source_url_type = models.SmallIntegerField(verbose_name='访问地址类型')
    source_module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, verbose_name='访问目标模块')
    source_tp_url = models.URLField(verbose_name='第三方访问地址', blank=True, null=True)
    custom_domain_url = models.URLField(verbose_name='绑定的独立域名访问地址', blank=True, null=True)
    prefer_https = models.BooleanField(null=True, verbose_name="当平台提供 https 协议时，是否优先使用")

    objects = MarketConfigManager()

    @property
    def market_address(self):
        """获取应用在市场里的唯一访问地址"""
        from paasng.publish.entrance.exposer import get_market_address

        return get_market_address(self.application)

    def on_release(self):
        """应用主模块正式环境上线 handler (尝试开启应用市场)
        如果 auto_enable_when_deploy == True 则开启市场, 并设置 auto_enable_when_deploy = False
        否则, 不做处理
        """
        if self.auto_enable_when_deploy:
            self.enabled = True
            self.auto_enable_when_deploy = False
            self.save(update_fields=['auto_enable_when_deploy', 'enabled'])

    def on_offline(self):
        """应用主模块正式环境下线 handler (关闭应用市场)
        如果 enabled == True, 则设置 auto_enable_when_deploy = True, 再设置 enabled = False
        """
        if self.enabled:
            self.auto_enable_when_deploy = True
            self.enabled = False
            self.save(update_fields=['auto_enable_when_deploy', 'enabled'])


@dataclass
class AvailableAddress:
    address: Optional[str]
    type: int

    def __post_init__(self):
        parse_result = urlparse(self.address)
        self.scheme = parse_result.scheme
        self.hostname = parse_result.hostname


CorpProduct = namedtuple('CorpProduct', 'id display_name')

DEFAULT_CORP_PRODUCTS = [
    CorpProduct('-1', "全业务"),
]

try:
    from .models_ext import get_all_corp_products
except ImportError:

    def get_all_corp_products() -> List[CorpProduct]:
        return DEFAULT_CORP_PRODUCTS
