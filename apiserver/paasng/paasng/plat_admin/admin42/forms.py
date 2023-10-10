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
from typing import Dict

from django.forms import CharField, ChoiceField, ModelChoiceField, ModelForm, Textarea

from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner
from paasng.core.region.states import RegionType


class ModelNameChoiceField(ModelChoiceField):
    def to_python(self, value):
        return super().to_python(value).name

    def __init__(
        self,
        queryset,
        *,
        empty_label="---------",
        required=True,
        widget=None,
        label=None,
        initial=None,
        help_text='',
        limit_choices_to=None,
        blank=False,
        **kwargs
    ):
        super().__init__(
            queryset,
            empty_label=empty_label,
            required=required,
            widget=widget,
            label=label,
            initial=initial,
            help_text=help_text,
            to_field_name="name",
            limit_choices_to=limit_choices_to,
            blank=blank,
            **kwargs
        )


class JSONEnvironmentFieldMixin:
    environments = CharField(widget=Textarea)
    data: Dict

    def clean_environments(self):
        return json.loads(self.data["environments"])


class AppSlugBuilderForm(ModelForm, JSONEnvironmentFieldMixin):
    region = ChoiceField(choices=RegionType.get_choices())

    class Meta:
        model = AppSlugBuilder
        exclude = ('updated', 'created', 'modules', 'buildpacks')


class AppSlugRunnerForm(ModelForm, JSONEnvironmentFieldMixin):
    region = ChoiceField(choices=RegionType.get_choices())
    name = ModelNameChoiceField(queryset=AppSlugBuilder.objects.all())

    class Meta:
        model = AppSlugRunner
        exclude = ('updated', 'created', 'modules')


class AppBuildPackForm(ModelForm, JSONEnvironmentFieldMixin):
    region = ChoiceField(choices=RegionType.get_choices())

    class Meta:
        model = AppBuildPack
        exclude = ('updated', 'created', 'modules')
