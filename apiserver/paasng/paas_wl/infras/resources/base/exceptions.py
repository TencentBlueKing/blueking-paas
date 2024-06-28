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


class KubeException(Exception):
    def __init__(self, *args, **kwargs):
        self.extra_value = kwargs.get("extra_value", None)
        super().__init__(*args)


class ResourceDuplicate(KubeException):
    def __init__(self, resource, resource_name, *args, **kwargs):
        msg = f"{resource}(name={resource_name}) has already existed"
        super().__init__(msg, *args, **kwargs)


class ReadTargetStatusTimeout(KubeException):
    def __init__(self, pod_name, max_seconds, *args, **kwargs):
        msg = "Checking status of pod:%s has exceeded %s seconds, give up." % (pod_name, max_seconds)
        super().__init__(msg, *args, **kwargs)


class PodNotSucceededError(KubeException):
    """pod not succeeded"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reason = kwargs.get("reason", "")
        self.message = kwargs.get("message", "")
        self.exit_code = kwargs.get("exit_code", -1)


class PodAbsentError(PodNotSucceededError):
    """pod not succeeded triggered by pod's absence"""


class PodTimeoutError(PodNotSucceededError):
    """pod not succeeded triggered by timeout"""


class CreateServiceAccountTimeout(KubeException):
    def __init__(self, namespace, timeout, *args, **kwargs):
        msg = "Namespace:%s which didn't create service account in %s seconds" % (namespace, timeout)
        KubeException.__init__(self, msg, *args, **kwargs)


class ResourceMissing(KubeException):
    def __init__(self, namespace, name, *args, **kwargs):
        msg = "Resource: <%s/%s> missing" % (namespace, name)
        KubeException.__init__(self, msg, *args, **kwargs)


class ResourceDeleteTimeout(KubeException):
    def __init__(self, resource_type, namespace, name, *args, **kwargs):
        if name != "":
            msg = f"{resource_type}<{namespace}/{name}> delete timeout"
        else:
            msg = f"{resource_type}<{namespace}> delete timeout"
        super().__init__(msg, *args, **kwargs)


class MapperNotInVersionError(Exception):
    """mapper is missing in this version"""


class NotAppScopedResource(Exception):
    """raise NotAppScopedResource If no WlApp object is found for the given kube_data"""
