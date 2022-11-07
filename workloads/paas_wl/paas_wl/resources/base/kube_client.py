# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict

from kubernetes.dynamic import DynamicClient, Resource
from kubernetes.dynamic.exceptions import ResourceNotUniqueError

logger = logging.getLogger(__name__)


class CoreDynamicClient(DynamicClient):
    """为官方 SDK 里的 DynamicClient 追加新功能"""

    def serialize_body(self, body: Any) -> Dict[str, Any]:
        """在执行任意接收 `body` 参数的资源操作类方法前，该方法被触发。它将尝试：

        - 把 OpenAPI 类型对象转换为字典
        - 把 ResourceInstance 对象转换为字典
        """
        # OpenAPI model object
        if getattr(body, 'openapi_types', None):
            return self.client.sanitize_for_serialization(body) or {}

        # dynamic ResourceInstance object
        if callable(getattr(body, 'to_dict', None)):
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
            'delete', path, body=body, label_selector=label_selector, field_selector=field_selector, **kwargs
        )

    def request(self, method, path, body=None, **params):
        # TODO: 包装转换请求异常
        return super().request(method, path, body=body, **params)


def patch_resource_field_cls():
    """Path original ResourceField class, raise exception when access a non-existent attribute"""

    def __getattr__(self, name):
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
