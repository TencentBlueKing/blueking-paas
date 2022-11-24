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
import re
from typing import Dict, Optional

from django.conf import settings
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from paasng.platform.applications.serializers import ApplicationField, AppNameField
from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n
from paasng.utils.serializers import RichTextField

from .constant import AppState, ProductSourceUrlType
from .models import DisplayOptions, MarketConfig, Product, Tag
from .signals import product_contact_updated, product_create_or_update_by_operator
from .utils import MarketAvailableAddressHelper


class AppLogoField(serializers.ImageField):
    def to_internal_value(self, logo):
        if logo.size >= 2 ** 21:
            raise ValidationError(_('文件太大, 大小不能超过2M'))

        if not re.match(r'^.+\.\w+$', logo.name):
            raise ValidationError(_('文件名格式非法'))

        return logo


class VisiableLabelsSlz(serializers.Serializer):
    id = serializers.IntegerField(label="ID")
    type = serializers.CharField(label="类型", min_length=1)
    name = serializers.CharField(label="名称", min_length=1)
    display_name = serializers.CharField(
        label="中文名", help_text="type 为 user 的时候有该字段，其他type没有该字段", allow_null=True, allow_blank=True, required=False
    )


class ProductTagField(serializers.SlugRelatedField):
    """Field class for Product Tag object, query tag by URL"""

    def __init__(self, *args, **kwargs):
        preset_kwargs = dict(
            slug_field='id',
            many=False,
            allow_empty=False,
            required=True,
            help_text="应用分类（按用途）",
        )
        preset_kwargs.update(kwargs)
        super().__init__(*args, **preset_kwargs)

    def get_queryset(self):
        return Tag.objects.all()

    def get_object(self, view_name, view_args, view_kwargs):
        """Overwrite the original method, add additional parent tag check"""
        obj = super().get_object(view_name, view_args, view_kwargs)
        return obj


class ProductTagByNameField(serializers.SlugRelatedField):
    """Field class for Product Tag object, query tag by name"""

    def __init__(self, *args, **kwargs):
        preset_kwargs = dict(
            slug_field='name',
            help_text="应用分类（按用途）",
        )
        preset_kwargs.update(kwargs)
        super().__init__(*args, **preset_kwargs)

    def get_queryset(self):
        return Tag.objects.all()

    def to_internal_value(self, data: str):
        """Overwrite the original method, add additional parent tag check"""
        try:
            obj = super().to_internal_value(data)
        except Tag.MultipleObjectsReturned:
            # 如果遇到同名的情形, 优先采用一级分类的 Tag
            obj = self.get_queryset().filter(**{self.slug_field: data}).order_by("parent").first()
        return obj


@i18n
class ProductBaseSLZ(serializers.Serializer):
    resizable = serializers.BooleanField(source="displayoptions.resizable", help_text=u"是否可调整窗口大小", required=False)
    width = serializers.IntegerField(source="displayoptions.width", help_text=u"窗口宽度", default=1200)
    height = serializers.IntegerField(source="displayoptions.height", help_text=u"窗口高度", default=600)
    is_win_maximize = serializers.BooleanField(source="displayoptions.is_win_maximize", help_text=u"窗口是否默认最大化")
    win_bars = serializers.BooleanField(source="displayoptions.win_bars", help_text=u"是否显示评分栏")

    # TODO: 当「修改市场信息」页面支持填写 i18n 字段时去除 write_only. (现在去掉 write_only 会导致市场信息无法被修改)
    name = I18NExtend(AppNameField(max_length=20, required=True, help_text=u"应用名称，不能超过20个字符", write_only=True))
    introduction = I18NExtend(serializers.CharField(help_text="应用简介", max_length=100, write_only=True))
    description = I18NExtend(RichTextField(help_text="应用描述", allow_blank=True, write_only=True))
    # 联系人非必填时，前端可能不传或者传空字符串
    contact = serializers.CharField(
        help_text=u"应用联系人",
        source="displayoptions.contact",
        required=settings.APP_REQUIRE_CONTACTS,
        allow_blank=(not settings.APP_REQUIRE_CONTACTS),
    )
    open_mode = serializers.CharField(help_text="打开方式", source="displayoptions.open_mode", required=False)
    related_corp_products = serializers.JSONField(help_text="所属业务")
    visiable_labels = serializers.ListField(
        help_text="可见范围", child=VisiableLabelsSlz(), allow_null=True, required=False
    )


class ProductCreateSLZ(serializers.ModelSerializer, ProductBaseSLZ):
    """注册新的市场应用"""

    logo = serializers.ImageField(write_only=True, allow_null=True, required=False)
    application = ApplicationField(
        slug_field='code',
        many=False,
        allow_null=True,
        help_text="应用id",
        validators=[UniqueValidator(queryset=Product.objects.all(), lookup="exact", message=u"该应用已经注册，请不要重复注册")],
    )
    tag = ProductTagField(slug_field="id")

    # Read-only fields
    name = TranslatedCharField(read_only=True)
    introduction = TranslatedCharField(read_only=True)
    description = TranslatedCharField(read_only=True)
    logo_url = serializers.ReadOnlyField(source="get_logo_url", help_text=u"上传Logo之后，应用Logo图片的下载地址")
    tag_name = serializers.ReadOnlyField(source="tag.get_name_display", help_text=u"Tag名称")
    code = serializers.ReadOnlyField(help_text="应用编码", source="application.code")

    class Meta(object):
        model = Product
        exclude = ('region', 'created', 'updated', 'owner')

    def validate(self, data: Dict):
        """Validate creation params"""
        data["code"] = data["application"].code
        data["owner"] = data["application"].owner
        return data

    def create(self, validated_data: Dict):
        """Overwrite default create action to create Product & DisplayOptions objects at once"""
        display_options = validated_data.pop("displayoptions", None)

        instance = super().create(validated_data)
        # Create DisplayOptions object
        if display_options:
            DisplayOptions.objects.create(product=instance, **display_options)
            product_contact_updated.send(sender=instance, product=instance)

        product_create_or_update_by_operator.send(
            sender=instance, product=instance, operator=self.context['request'].user.pk, created=True
        )
        return instance


class ProductCombinedSLZ(serializers.ModelSerializer, ProductBaseSLZ):
    tag = ProductTagField(slug_field="id")

    # Read-only fields
    name = TranslatedCharField(read_only=True)
    introduction = TranslatedCharField(read_only=True)
    description = TranslatedCharField(read_only=True)
    application = serializers.ReadOnlyField(source="application__code")
    code = serializers.ReadOnlyField(help_text="应用编码")
    logo = serializers.ReadOnlyField(source='get_logo_url', help_text=u"应用的logo地址，需要单独用接口上传")
    tag_name = serializers.ReadOnlyField(source="tag.get_name_display", help_text=u"Tag名称")

    class Meta(object):
        model = Product
        exclude = ('region', 'created', 'updated', 'owner')

    @atomic
    def update(self, instance: Product, validated_data: Dict):
        """注意：该接口支持局部更新，处理字段前都需要判断下有没有传这个字段"""
        display_options = validated_data.pop("displayoptions", None)
        instance = super().update(instance, validated_data)

        # Process Display Options
        if display_options:
            super().update(instance.displayoptions, display_options)
            # Send signal when contact has been modified
            if 'contact' in display_options:
                product_contact_updated.send(sender=instance, product=instance)

        # After saving display options, synchronize the data, otherwise it will cause the delay of synchronization
        product_create_or_update_by_operator.send(
            sender=instance, product=instance, operator=self.context['request'].user.pk, created=False
        )
        return instance


class TagSLZ(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='api.market.tags.detail', lookup_field='id')

    parent = serializers.IntegerField(help_text=u"父节点ID", source="parent.id", default=None)

    id = serializers.IntegerField(help_text=u"主键")

    name = serializers.CharField(source="get_name_display")

    class Meta(object):
        model = Tag
        fields = ("url", "id", "name", "parent", "remark", "index", "region")


class ProductStateSLZ(serializers.ModelSerializer):
    class Meta(object):
        model = Product
        fields = ['state']

    def validate_state(self, value):
        try:
            AppState(value)
        except ValueError:
            raise serializers.ValidationError(_("不支持的操作类型"))


class ProductLogoSLZ(serializers.ModelSerializer):
    logo = serializers.ImageField(write_only=True)
    logo_url = serializers.ReadOnlyField(source="get_logo_url", help_text=u"上传Logo之后，应用Logo图片的下载地址")
    code = serializers.ReadOnlyField(help_text=u"应用编码")

    class Meta(object):
        model = Product
        fields = ['logo', 'code', 'logo_url']

    @atomic
    def update(self, instance, validated_data):
        result = super(ProductLogoSLZ, self).update(instance, validated_data)
        product_create_or_update_by_operator.send(
            sender=instance, product=instance, operator=self.context['request'].user.pk, created=False
        )
        return result


class ProductOfflineSLZ(serializers.Serializer):
    recyle_online_resource = serializers.BooleanField(default=False)


class MarketConfigSLZ(serializers.ModelSerializer):
    source_tp_url = serializers.URLField(required=False, allow_blank=True, allow_null=True, help_text="第三方访问地址")
    custom_domain_url = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, help_text="绑定的独立域名访问地址"
    )
    source_url_type = serializers.ChoiceField(
        choices=ProductSourceUrlType.get_choices(),
        required=False,
        help_text="访问地址类型\n" + " ".join(map(str, ProductSourceUrlType.get_choices())),
    )
    prefer_https = serializers.NullBooleanField(required=False, help_text="是否偏好 HTTPS")

    source_module_id = serializers.UUIDField(allow_null=True, required=False, help_text="绑定模块id", read_only=True)
    enabled = serializers.BooleanField(read_only=True, help_text="是否上架到市场")
    market_address = serializers.URLField(read_only=True, allow_blank=True, allow_null=True, help_text="市场访问链接")

    class Meta(object):
        model = MarketConfig
        fields = [
            'enabled',
            'source_url_type',
            'source_tp_url',
            'source_module_id',
            'market_address',
            'custom_domain_url',
            'prefer_https',
        ]

    def update(self, instance: MarketConfig, validated_data: Dict):
        source_url_type = validated_data.get("source_url_type")
        source_tp_url = validated_data.get('source_tp_url')
        custom_domain_url = validated_data.get('custom_domain_url')

        if source_tp_url and source_url_type == ProductSourceUrlType.THIRD_PARTY.value:
            self._regulate_source_tp_url(instance, validated_data)

        if custom_domain_url and source_url_type == ProductSourceUrlType.CUSTOM_DOMAIN.value:
            self._regulate_custom_domain_url(instance, validated_data)

        if source_url_type == ProductSourceUrlType.ENGINE_PROD_ENV_HTTPS.value:
            validated_data["prefer_https"] = True

        return super().update(instance, validated_data)

    @staticmethod
    def _regulate_custom_domain_url(instance: MarketConfig, validated_data: Dict):
        """Validate custom_domain_url field and source_url_type field"""
        custom_domain_url: Optional[str] = validated_data.get('custom_domain_url')
        if not custom_domain_url:
            raise RuntimeError('no custom_domain_url provided')

        available_address = MarketAvailableAddressHelper(instance).filter_domain_address(address=custom_domain_url)
        if available_address is None:
            raise ValidationError(_('当前模块的生产环境未绑定该访问地址'))

        # 不使用前端透传的 source_url_type
        validated_data['source_url_type'] = available_address.type

    @staticmethod
    def _regulate_source_tp_url(instance: MarketConfig, validated_data: Dict):
        """Validate source_tp_url field and source_url_type field, only support engineless app"""
        application = instance.application

        if not validated_data.get("source_tp_url"):
            raise ValidationError("source_tp_url should not be null")

        if application.engine_enabled:
            raise ValidationError("source_tp_url only support for engineless app")

        # 不使用前端透传的 source_url_type
        validated_data['source_url_type'] = ProductSourceUrlType.THIRD_PARTY.value


class AvailableAddressSLZ(serializers.Serializer):
    address = serializers.URLField(required=True)
    type = serializers.ChoiceField(
        choices=ProductSourceUrlType.get_choices(),
        required=True,
        help_text=" ".join(map(str, ProductSourceUrlType.get_choices())),
    )


class AvailableAddressFullySLZ(AvailableAddressSLZ):
    hostname = serializers.CharField()
    scheme = serializers.CharField()


class FailedProconditionSLZ(serializers.Serializer):
    message = serializers.CharField()
    action_name = serializers.CharField()


class PublishProtectionSLZ(serializers.Serializer):
    all_conditions_matched = serializers.BooleanField()
    failed_conditions = FailedProconditionSLZ(many=True)
