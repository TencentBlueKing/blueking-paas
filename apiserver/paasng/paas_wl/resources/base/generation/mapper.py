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
from contextlib import contextmanager
from functools import partial
from typing import TYPE_CHECKING, Callable, Generic, Optional, Tuple, Type, TypeVar

from paas_wl.resources.base.kres import BaseKresource, KDeployment, KPod, KReplicaSet

if TYPE_CHECKING:
    from paas_wl.resources.base.base import EnhancedApiClient
    from paas_wl.workloads.processes.models import Process


MapperResource = TypeVar("MapperResource", bound=BaseKresource)


class Mapper(Generic[MapperResource]):
    """映射器，用于将 WlApp 映射到 k8s 资源"""

    # 主要映射两种东西：
    # - 属性值
    # - 具体到 k8s 的行为

    # 前者是简单的名字转换，类似 v1 pod 名称是 xxx, v2 pod 名称是 yyy
    # 后者是行为的不同: v1 pod 通过 get() 方法获取(from NameBasedOperations),
    #                v2 pod 则是通过 list() 获取(from LabelBasedOperations)
    # 这里的行为映射，并不只是 kres 的等量替换，而是在 kres 上的一层封装

    kres_class: Type[MapperResource]

    def __init__(self, process: 'Process', client: Optional['EnhancedApiClient'] = None):
        self.process = process
        self.client = client

    ##############
    # attributes #
    ##############
    @property
    def name(self) -> str:
        """获取资源名"""
        raise NotImplementedError

    @property
    def labels(self) -> dict:
        """创建该资源时添加的 labels"""
        raise NotImplementedError

    @property
    def match_labels(self) -> dict:
        """用于匹配该资源时使用的 labels"""
        raise NotImplementedError

    @property
    def pod_selector(self) -> str:
        """用户匹配 pod 的选择器"""
        raise NotImplementedError

    @property
    def namespace(self):
        """对于目前所有资源，namespace 都和 process 保持一致"""
        return self.process.app.namespace


class CallThroughKresMapper(Mapper, Generic[MapperResource]):
    """针对特定版本，只需要代理指向 kres 请求"""

    @contextmanager
    def kres(self):
        """Return kres object as a context manager which was initialized with kubernetes client, will close all
        connection automatically when exit to avoid connections leaking.
        """
        if self.client is None:
            raise ValueError("client is required when calling kres")

        with self.client:
            yield self.kres_class(self.client)

    def _kres_call_through(self, method: str, use_label_based: bool = False) -> Callable:
        with self.kres() as target_obj:
            if use_label_based:
                target_obj = target_obj.ops_label
            return getattr(target_obj, method)

    def get(self) -> MapperResource:
        """get 方法快捷注入"""
        return self._kres_call_through("get")(name=self.name, namespace=self.namespace)

    def create(self, body) -> MapperResource:
        """get 方法快捷注入"""
        return self._kres_call_through("create")(name=self.name, namespace=self.namespace, body=body)

    def replace_or_patch(self, body) -> MapperResource:
        """replace_or_patch 方法快捷注入"""
        return self._kres_call_through("replace_or_patch")(body=body, name=self.name, namespace=self.namespace)

    def create_or_update(self, body, update_method: str = "replace") -> Tuple[MapperResource, bool]:
        """create_or_update 方法快捷注入"""
        return self._kres_call_through("create_or_update")(
            body=body, update_method=update_method, name=self.name, namespace=self.namespace
        )

    def delete(self, non_grace_period: bool = True):
        """delete 方法快捷注入"""
        return self._kres_call_through("delete")(
            non_grace_period=non_grace_period, name=self.name, namespace=self.namespace
        )

    def delete_individual(self):
        """delete_individual 方法快捷注入"""
        return self._kres_call_through("delete_individual", use_label_based=True)(
            labels=self.match_labels, namespace=self.namespace
        )

    def delete_collection(self, non_grace_period: bool = True):
        """delete_collection 方法快捷注入"""
        return self._kres_call_through("delete_collection", use_label_based=True)(
            labels=self.match_labels, namespace=self.namespace
        )


class MapperField(Generic[MapperResource]):
    """MapperField 使用描述符协议为 CallThroughKresMapper 提供默认的 client 属性"""

    def __init__(self, mapper_class: Type[CallThroughKresMapper[MapperResource]]):
        self.mapper_class = mapper_class

    def __call__(
        self, instance: 'MapperPack', process: 'Process', client: Optional['EnhancedApiClient'] = None
    ) -> CallThroughKresMapper[MapperResource]:
        return self.mapper_class(process=process, client=client or instance.client)

    def __get__(
        self, instance: Optional['MapperPack'], owner: Type['MapperPack']
    ) -> Callable[..., CallThroughKresMapper[MapperResource]]:
        if instance is None:
            return self
        return partial(self.__call__, instance)


class MapperPack:
    _ignore_command_name = False
    version: str
    pod: MapperField[KPod]
    deployment: MapperField[KDeployment]
    replica_set: MapperField[KReplicaSet]

    def __init__(self, client: Optional['EnhancedApiClient'] = None):
        # client can only be used at CallThroughKresMapper
        # never be used at Mapper
        self.client = client

    @property
    def ignore_command_name(self) -> bool:
        return self._ignore_command_name
