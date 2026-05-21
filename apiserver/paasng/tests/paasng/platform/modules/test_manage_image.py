# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

import pytest
from django.core.management import call_command

from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner

pytestmark = pytest.mark.django_db


class TestManageImageDefaultFlag:
    """测试 manage_image 命令的 --default 参数"""

    def _call_manage_image(self, name, image="test-image:latest", type_="cnb", default=False, **kwargs):
        """辅助方法：调用 manage_image 命令"""
        args = [
            "--name",
            name,
            "--type",
            type_,
            "--slugbuilder",
            image,
            "--slugrunner",
            image,
            "--display_name_zh_cn",
            "测试镜像",
            "--display_name_en",
            "Test Image",
            "--description_zh_cn",
            "测试描述",
            "--description_en",
            "Test description",
        ]
        if default:
            args.append("--default")
        call_command("manage_image", *args)

    def test_set_default_when_no_existing_default(self):
        """场景 1：传入 --default 且无已有默认镜像时，is_default 被设置为 True"""
        self._call_manage_image("test-cloudnative", default=True)

        builder = AppSlugBuilder.objects.get(name="test-cloudnative")
        runner = AppSlugRunner.objects.get(name="test-cloudnative")

        assert builder.is_default is True
        assert runner.is_default is True

    def test_skip_default_when_existing_default(self):
        """场景 2：传入 --default 但已存在默认镜像时，is_default 不被修改"""
        # 先创建一个已有的默认镜像
        self._call_manage_image("existing-default", default=True)

        # 再尝试设置另一个为默认
        self._call_manage_image("test-cloudnative", default=True)

        existing_builder = AppSlugBuilder.objects.get(name="existing-default")
        new_builder = AppSlugBuilder.objects.get(name="test-cloudnative")
        existing_runner = AppSlugRunner.objects.get(name="existing-default")
        new_runner = AppSlugRunner.objects.get(name="test-cloudnative")

        # 已有默认保持不变
        assert existing_builder.is_default is True
        assert existing_runner.is_default is True
        # 新镜像不会被设置为默认
        assert new_builder.is_default is False
        assert new_runner.is_default is False

    def test_no_default_flag_does_not_affect_is_default(self):
        """场景 3：未传入 --default 时，is_default 字段不受影响"""
        self._call_manage_image("test-image")

        builder = AppSlugBuilder.objects.get(name="test-image")
        runner = AppSlugRunner.objects.get(name="test-image")

        assert builder.is_default is False
        assert runner.is_default is False

    def test_idempotent_execution(self):
        """场景 4：多次执行同一命令（幂等性验证）"""
        # 第一次执行
        self._call_manage_image("test-cloudnative", default=True)
        # 第二次执行
        self._call_manage_image("test-cloudnative", default=True)

        builder = AppSlugBuilder.objects.get(name="test-cloudnative")
        runner = AppSlugRunner.objects.get(name="test-cloudnative")

        assert builder.is_default is True
        assert runner.is_default is True
        # 确保只有一条记录
        assert AppSlugBuilder.objects.filter(name="test-cloudnative").count() == 1
        assert AppSlugRunner.objects.filter(name="test-cloudnative").count() == 1
