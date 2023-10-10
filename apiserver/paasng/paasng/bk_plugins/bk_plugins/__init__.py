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
"""Module for bk_plugin type application

“BkPlugin（蓝鲸插件）”是一个基于蓝鲸应用构建的抽象概念，它实际上就是一个蓝鲸应用，
只是多了一些定制化，比如：

- 创建 BkPlugin 不需要选择任何代码初始化模板
- BkPlugin 不允许上线到“蓝鲸市场”

本模块提供了一些与 BkPlugin 有关的系统 API，以方便其他平台接入并使用功能。这些 API
在返回插件数据时，刻意用了与普通 Application 不同的结构，屏蔽了一些字段，这是有意为之。
不直接使用 Application 结构，我们就能更方便的在后期针对插件做定制。
"""
default_app_config = 'paasng.bk_plugins.bk_plugins.apps.BkPluginsAppConfig'
