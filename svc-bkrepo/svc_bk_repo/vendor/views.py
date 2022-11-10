# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging

from django.conf import settings
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from paas_service.auth.decorator import instance_authorized_require
from paas_service.models import ServiceInstance
from paas_service.utils import get_paas_app_info
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from svc_bk_repo.vendor.actions import extend_quota
from svc_bk_repo.vendor.exceptions import ExtendQuotaMaxSizeExceeded, ExtendQuotaUsageTooLow, NoNeedToExtendQuota
from svc_bk_repo.vendor.helper import BKGenericRepoManager
from svc_bk_repo.vendor.render import humanize_bytes
from svc_bk_repo.vendor.serializers import ServiceInstanceForManageSLZ

logger = logging.getLogger(__name__)


class HealthzView(APIView):
    def get(self, request):
        return Response(
            {
                "result": True,
                "data": {},
                "message": "",
            }
        )


@method_decorator(instance_authorized_require, name="get")
class BKRepoIndexView(TemplateView):
    permission_classes = [IsAuthenticated]
    template_name = "index.html"
    name = "首页"

    def get_context_data(self, **kwargs):
        instance = get_object_or_404(ServiceInstance, pk=self.kwargs['instance_id'])

        plan_config = instance.plan.get_config()
        manager = BKGenericRepoManager(**plan_config)

        credentials = instance.get_credentials()
        private_bucket = credentials["private_bucket"]
        public_bucket = credentials["public_bucket"]

        private_quota = manager.get_repo_quota(private_bucket)
        public_quota = manager.get_repo_quota(public_bucket)

        if 'view' not in kwargs:
            kwargs['view'] = self

        kwargs["private_bucket"] = private_bucket
        kwargs["private_quota"] = private_quota
        kwargs["public_bucket"] = public_bucket
        kwargs["public_quota"] = public_quota

        kwargs["app_info"] = get_paas_app_info(instance)
        kwargs["instance"] = ServiceInstanceForManageSLZ(instance).data
        kwargs["csrftoken"] = get_token(self.request)
        kwargs["uid"] = self.request.user.username

        return kwargs


class BKRepoManageView(APIView):
    @method_decorator(instance_authorized_require)
    def patch(self, request, instance_id, bucket):
        """自助扩容"""
        instance = get_object_or_404(ServiceInstance, uuid=instance_id)

        plan_config = instance.plan.get_config()
        manager = BKGenericRepoManager(**plan_config)

        credentials = instance.get_credentials()
        private_bucket = credentials["private_bucket"]
        public_bucket = credentials["public_bucket"]

        if bucket not in [private_bucket, public_bucket]:
            return Response({"message": "不支持扩容当前仓库."})

        try:
            max_size_bytes = extend_quota(
                manager,
                bucket=bucket,
                extra_size_bytes=settings.EXTEND_CONFIG_EXTRA_SIZE_BYTES,
                max_allowed_bytes=settings.EXTEND_CONFIG_MAX_SIZE_ALLOWED,
                required_usage_rate=50,
            )
        except NoNeedToExtendQuota:
            logger.info("仓库: %s 未配置容量配额, 无需扩容.", bucket)
            return Response({"message": "未配置容量配额, 无需扩容."})
        except ExtendQuotaMaxSizeExceeded:
            human_max_size = humanize_bytes(settings.EXTEND_CONFIG_MAX_SIZE_ALLOWED)
            return Response({"message": f'最大扩容容量不能超过 {human_max_size}'}, status=status.HTTP_400_BAD_REQUEST)
        except ExtendQuotaUsageTooLow:
            return Response({"message": "空闲容量大于 50%, 不支持自助扩容"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"message": "未知异常, 请稍后重试"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": f"{bucket} 的容量已修改成 {humanize_bytes(max_size_bytes)}"})
