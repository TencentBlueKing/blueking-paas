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


class EmptyAppIngressError(Exception):
    """Exception raised when trying to sync an ingress with no domains"""


class ValidCertNotFound(Exception):
    """When syncing a https domain, if we can not find a valid tls certificate. This exception
    is raised.
    """


class DefaultServiceNameRequired(Exception):
    """When trying to create a new ingress resource without a default service_name, this exception is
    raised
    """


class PersistentAppDomainRequired(Exception):
    """When performing some actions, a presistent(stored in database) AppDomain object is required,
    this includes generating an ingress name for a domain with customized subpath -- the primary key
    of AppDomain object is necessary part.
    """
