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
from typing import List, NamedTuple

from django.db import migrations

from paasng.platform.engine.models import DeployPhaseTypes


class BuildStepMetaData(NamedTuple):
    name: str
    started_patterns: List[str]
    finished_patterns: List[str]


def add_cnb_step_meta_set(apps, schema_editor):
    build_step_data = [
        BuildStepMetaData(
            name="初始化构建环境",
            # 第 1 列是 slug-pilot, 第 2 列是 cnb
            started_patterns=["-----> Step setup begin", "Setup Build Environ"],
            finished_patterns=["\\s+Step setup done", "\\s+Starting builder..."],
        ),
        BuildStepMetaData(
            name="分析构建方案",
            # 第 1 列是 slug-pilot, 第 2 列是 cnb
            started_patterns=["-----> Step analysis begin", "Analyzing optimization plan"],
            finished_patterns=["\\s+Step analysis done", "\\s+Step Analyze done"],
        ),
        BuildStepMetaData(
            name="检测构建工具",
            # 第 1 列是 slug-pilot, 第 2 列是 cnb
            started_patterns=["-----> Step detect begin", "Detecting Buildpacks..."],
            finished_patterns=["\\s+Step detect done", "\\s+Step Detect done"],
        ),
        BuildStepMetaData(
            name="构建应用",
            # 第 1 列是 default, 第 2 列是 slug-pilot, 第 3 列是 cnb
            started_patterns=["-----> Compiling app...", "-----> Step build begin", "Building application..."],
            finished_patterns=["-----> Discovering process types", "\\s+Step build done", "\\s+Step Build done"],
        ),
        BuildStepMetaData(
            # 第 1 列是 cnb
            name="上传镜像", started_patterns=["Exporting image..."], finished_patterns=["\\s+Step Export done"]
        ),
    ]

    DeployStepMeta = apps.get_model("engine", "DeployStepMeta")
    metas = [
        # 上云环境有多条记录 :(
        DeployStepMeta.objects.filter(name="解析应用进程信息").last(),
        DeployStepMeta.objects.filter(name="上传仓库代码").last(),
        DeployStepMeta.objects.filter(name="配置资源实例").last(),
    ]

    for step in build_step_data:
        obj, _ = DeployStepMeta.objects.update_or_create(
            name=step.name,
            phase=DeployPhaseTypes.BUILD.value,
            defaults={"started_patterns": step.started_patterns, "finished_patterns": step.finished_patterns},
        )
        metas.append(obj)

    metas.extend(
        [
            DeployStepMeta.objects.filter(name="部署应用").last(),
            DeployStepMeta.objects.filter(name="执行部署前置命令").last(),
            DeployStepMeta.objects.filter(name="检测部署结果").last(),
        ]
    )

    StepMetaSet = apps.get_model("engine", "StepMetaSet")
    meta_set = StepMetaSet.objects.create(is_default=True, name="cnb")

    for meta in metas:
        meta_set.metas.add(meta)


class Migration(migrations.Migration):
    dependencies = [
        ("engine", "0019_auto_20231214_1547"),
    ]

    operations = [
        migrations.RunPython(add_cnb_step_meta_set),
    ]
