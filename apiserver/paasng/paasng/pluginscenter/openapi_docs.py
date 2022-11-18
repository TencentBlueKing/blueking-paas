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
from drf_yasg import openapi

from paasng.pluginscenter import constants, definitions

create_plugin_instance_schema = openapi.Schema(
    description="创建插件实例的Schema",
    type=openapi.TYPE_OBJECT,
    properties={
        "plugin_type": openapi.Schema(
            title="plugin_type",
            type=openapi.TYPE_OBJECT,
            properties={
                "id": openapi.Schema(title="id", description="插件类型标识", type=openapi.TYPE_STRING),
                "name": openapi.Schema(title="name", description="插件类型名称", type=openapi.TYPE_STRING),
                "description": openapi.Schema(title="description", description="插件类型描述", type=openapi.TYPE_STRING),
                "docs": openapi.Schema(
                    title="docs", description="插件类型说明文档", type=openapi.TYPE_STRING, format=openapi.FORMAT_URI
                ),
                "logo": openapi.Schema(title="logo", description="插件类型logo", type=openapi.TYPE_STRING),
            },
        ),
        "schema": openapi.Schema(
            title="create-plugin-instance-schema",
            type=openapi.TYPE_OBJECT,
            properties={
                "id": openapi.Schema(**definitions.FieldSchema.schema()),
                "name": openapi.Schema(**definitions.FieldSchema.schema()),
                "init_templates": openapi.Schema(
                    type=openapi.TYPE_ARRAY, items=openapi.Schema(**definitions.PluginCodeTemplate.schema())
                ),
                "release_method": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="发布方式",
                    enum=[constants.PluginReleaseMethod.CODE],
                ),
                "repository_group": openapi.Schema(
                    description="项目仓库组",
                    type=openapi.TYPE_STRING,
                ),
                "repository_template": openapi.Schema(
                    description="项目仓库模板",
                    type=openapi.TYPE_STRING,
                ),
                "extra_fields": openapi.Schema(
                    description="额外字段定义",
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "< * >": openapi.Schema(**definitions.FieldSchema.schema()),
                    },
                ),
            },
        ),
    },
)


create_plugin_instance_schemas = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=create_plugin_instance_schema,
)


market_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "category": openapi.Schema(
            type=openapi.TYPE_ARRAY, description="可选的标签/分类", items=openapi.Schema(type=openapi.TYPE_STRING)
        ),
        "schema": openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "extra_fields": openapi.Schema(
                    description="额外字段定义",
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "< * >": openapi.Schema(**definitions.FieldSchema.schema()),
                    },
                ),
            },
        ),
        "readonly": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="市场信息是否可编辑"),
    },
)


create_release_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "docs": openapi.Schema(description="说明文档地址", type=openapi.TYPE_STRING),
        "source_version_pattern": openapi.Schema(
            description="校验代码版本(source_version_name)正则表达式模板, 留空则不校验", type=openapi.TYPE_STRING
        ),
        "version_no": openapi.Schema(
            description="版本号生成规则, 自动生成(automatic)," "与代码版本一致(revision)," "与提交哈希一致(commit-hash)," "用户自助填写(self-fill)",
            type=openapi.TYPE_STRING,
            enum=["automatic", "revision", "commit-hash", "self-fill"],
        ),
        "extra_fields": openapi.Schema(
            description="额外字段定义",
            type=openapi.TYPE_OBJECT,
            properties={
                "< * >": openapi.Schema(**definitions.FieldSchema.schema()),
            },
        ),
        "source_versions": openapi.Schema(
            description="可选的代码分支",
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                description="源码版本",
                type=openapi.TYPE_OBJECT,
                properties={
                    "name": openapi.Schema(
                        description="分支名/Tag名",
                        type=openapi.TYPE_STRING,
                    ),
                    "type": openapi.Schema(description="源码版本类型", type=openapi.TYPE_STRING, enum=["branch", "tag"]),
                },
            ),
        ),
        "semver_choices": openapi.Schema(
            description="版本类型选项",
            type=openapi.TYPE_OBJECT,
            properties={
                "major": openapi.Schema(
                    description="下一个重大版本",
                    type=openapi.TYPE_STRING,
                ),
                "minor": openapi.Schema(
                    description="下一个次版本",
                    type=openapi.TYPE_STRING,
                ),
                "patch": openapi.Schema(
                    description="下一个修正版本",
                    type=openapi.TYPE_STRING,
                ),
            },
        ),
        "current_release": openapi.Schema(
            description="当前版本",
            type=openapi.TYPE_OBJECT,
            properties={
                "version": openapi.Schema(
                    description="版本号",
                    type=openapi.TYPE_STRING,
                ),
                "source_version_type": openapi.Schema(
                    description="代码版本类型(branch/tag)",
                    type=openapi.TYPE_STRING,
                ),
                "source_version_name": openapi.Schema(
                    description="代码分支名/tag名",
                    type=openapi.TYPE_STRING,
                ),
                "source_hash": openapi.Schema(
                    description="代码提交哈希",
                    type=openapi.TYPE_STRING,
                ),
                "creator": openapi.Schema(
                    description="部署人",
                    type=openapi.TYPE_STRING,
                ),
                "created": openapi.Schema(
                    description="部署时间",
                    type=openapi.TYPE_STRING,
                ),
            },
        ),
    },
)


plugin_basic_info_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(**definitions.FieldSchema.schema()),
        "name": openapi.Schema(**definitions.FieldSchema.schema()),
        "extra_fields": openapi.Schema(
            description="额外字段定义",
            type=openapi.TYPE_OBJECT,
            properties={
                "< * >": openapi.Schema(**definitions.FieldSchema.schema()),
            },
        ),
    },
)
