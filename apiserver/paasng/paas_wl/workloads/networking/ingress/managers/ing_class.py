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

from django.conf import settings

from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.constants import ClusterAnnotationKey
from paas_wl.infras.cluster.utils import get_cluster_by_app


def get_ingress_class_by_wl_app(wl_app: WlApp) -> str | None:
    # 集群注解中指定 IngressClassName 的情况
    annos = get_cluster_by_app(wl_app).annotations
    if cls_name := annos.get(ClusterAnnotationKey.INGRESS_CLASS_NAME):
        return cls_name

    # 特殊指定 IngressClassName 的情况
    return settings.APP_INGRESS_CLASS
