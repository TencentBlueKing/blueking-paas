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

import logging
from typing import Any, Dict

from kubernetes.dynamic import DynamicClient, Resource
from kubernetes.dynamic.discovery import LazyDiscoverer as _LazyDiscoverer
from kubernetes.dynamic.discovery import ResourceGroup
from kubernetes.dynamic.exceptions import DynamicApiError, NotFoundError, ResourceNotFoundError, ResourceNotUniqueError

logger = logging.getLogger(__name__)


class LazyDiscoverer(_LazyDiscoverer):
    """LazyDiscoverer fixed cache bug

    Note: You cannot change the name `LazyDiscoverer`, otherwise the override will not work
    """

    def __search(self, parts, resources, reqParams):  # noqa
        part = parts[0]
        if part != "*":
            resourcePart = resources.get(part)  # noqa
            if not resourcePart:
                return []
            elif isinstance(resourcePart, ResourceGroup):
                if len(reqParams) != 2:
                    raise ValueError("prefix and group params should be present, have %s" % reqParams)
                # Check if we've requested resources for this group
                if not resourcePart.resources:
                    prefix, group, version = reqParams[0], reqParams[1], part
                    try:
                        resourcePart.resources = self.get_resources_for_api_version(
                            prefix, group, part, resourcePart.preferred
                        )
                    except NotFoundError:
                        raise ResourceNotFoundError

                    # https://github.com/kubernetes-client/python/blob/master/kubernetes/base/dynamic/discovery.py#L271
                    # kubernetes python sdk will always update cache even if the resourcePart is not updated
                    # in order to avoid unnecessary disk writing, only update cache when resourcePart.resources is set
                    if resourcePart.resources:
                        self._cache["resources"][prefix][group][version] = resourcePart
                        self.__update_cache = True
                return self.__search(parts[1:], resourcePart.resources, reqParams)
            elif isinstance(resourcePart, dict):
                # In this case parts [0] will be a specified prefix, group, version
                # as we recurse
                return self.__search(parts[1:], resourcePart, reqParams + [part])
            else:  # noqa
                if parts[1] != "*" and isinstance(parts[1], dict):
                    for _resource in resourcePart:
                        for term, value in parts[1].items():
                            if getattr(_resource, term) == value:
                                return [_resource]
                    return []
                else:
                    return resourcePart
        else:
            matches = []
            for key in resources.keys():  # noqa: SIM118
                matches.extend(self.__search([key] + parts[1:], resources, reqParams))
            return matches


class CoreDynamicClient(DynamicClient):
    """为官方 SDK 里的 DynamicClient 追加新功能"""

    def __init__(self, client, cache_file=None, discoverer=None):
        super().__init__(client, cache_file, discoverer=discoverer or LazyDiscoverer)

    def serialize_body(self, body: Any) -> Dict[str, Any]:
        """在执行任意接收 `body` 参数的资源操作类方法前，该方法被触发。它将尝试：

        - 把 OpenAPI 类型对象转换为字典
        - 把 ResourceInstance 对象转换为字典
        """
        # OpenAPI model object
        if getattr(body, "openapi_types", None):
            return self.client.sanitize_for_serialization(body) or {}

        # dynamic ResourceInstance object
        if callable(getattr(body, "to_dict", None)):
            return body.to_dict()
        return body or {}

    def get_preferred_resource(self, kind: str) -> Resource:
        """尝试获取动态 Resource 对象，优先使用 preferred=True 的 ApiGroup

        :param kind: 资源种类，比如 Deployment
        :raises: ResourceNotUniqueError 匹配到多个不同版本资源，ResourceNotFoundError 没有找到资源
        """
        try:
            return self.resources.get(kind=kind, preferred=True)
        except ResourceNotUniqueError:
            # 如果使用 preferred=True 仍然能匹配到多个 ApiGroup，使用第一个结果
            resources = self.resources.search(kind=kind, preferred=True)
            return resources[0]

    def delete_anyway(
        self, resource, name=None, namespace=None, body=None, label_selector=None, field_selector=None, **kwargs
    ):
        """调用删除接口，但不验证参数是否正确。
        用来解决普通的 .delete() 方法必须校验 label_selector 非空问题。
        """
        path = resource.path(name=name, namespace=namespace)
        return self.request(
            "delete", path, body=body, label_selector=label_selector, field_selector=field_selector, **kwargs
        )

    def request(self, method, path, body=None, **params):
        try:
            return super().request(method, path, body=body, **params)
        except DynamicApiError as e:
            # 去除原始异常中的 tb 信息, 这些信息不适合直接抛出
            raise type(e)(e, tb=None)


def patch_resource_field_cls():
    """Path original ResourceField class, raise exception when access a non-existent attribute"""

    def __getattr__(self, name):  # noqa: N807
        """The original `ResourceField.__getattr__` will return `None` silently when getting a non-existent
        attribute, this function raise an exception instead.

        :raise AttributeError: when required name does not existed
        """
        try:
            return getattr(self.__dict__, name)
        except AttributeError:
            try:
                return self.__dict__[name]
            except KeyError:
                raise AttributeError(f'current field has no "{name}" attribute')

    from kubernetes.dynamic.resource import ResourceField

    ResourceField.__getattr__ = __getattr__


patch_resource_field_cls()
