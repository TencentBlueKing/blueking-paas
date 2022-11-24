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
"""Authentication between internal services, most codes were copied from paas-service package(0.2.0)
TODO: remove duplications between "paas-service" and current module by abstract a new package?
"""
import logging

from django.http import HttpRequest
from rest_framework.authentication import BaseAuthentication

from paas_wl.utils.error_codes import error_codes

logger = logging.getLogger(__name__)


class VerifiedClientRequired(BaseAuthentication):
    """Only allow requests carrying verified client info"""

    def authenticate(self, request: HttpRequest):
        client = getattr(request, 'client', None)
        if client and client.is_verified():
            # Return a none result to let other authentication classes proceed
            return None
        else:
            raise error_codes.SERVICE_AUTH_FAILED
