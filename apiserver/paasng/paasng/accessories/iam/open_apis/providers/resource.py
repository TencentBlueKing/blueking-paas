# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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
from typing import Dict, List, Optional, Tuple, Type, Union

from iam.collection import FancyDict
from iam.resource.provider import ResourceProvider
from iam.resource.utils import Page, get_filter_obj, get_page_obj

from paasng.accessories.iam.constants import ResourceType

from .application import ApplicationProvider

PROVIDER_CLS_MAP: Dict[ResourceType, Type[ResourceProvider]] = {
    ResourceType.Application: ApplicationProvider,
}


class BKPaaSResourceProvider:
    def __init__(self, resource_type: ResourceType):
        """
        :param resource_type: 资源类型 如 application 等
        """
        self.resource_provider = PROVIDER_CLS_MAP[resource_type]()

    def provide(self, method: str, data: Dict, **options) -> Union[List, Dict]:
        """
        根据 method 值, 调用对应的方法返回数据

        :param method: 值包括 list_attr, list_attr_value, list_instance 等
        :param data: 其他查询条件数据，如分页数据等
        :return: method 方法返回的数据
        """
        handler = getattr(self, method)
        return handler(data, **options)

    def list_attr(self, data: Optional[Dict] = None, **options) -> List[Dict]:
        """
        查询某个资源类型可用于配置权限的属性列表

        :param data: 占位参数，为了 self.provide 方法的处理统一
        :return: 属性列表
        """
        result = self.resource_provider.list_attr(**options)
        return result.to_list()

    def list_attr_value(self, data: Dict, **options) -> Dict:
        """获取一个资源类型某个属性的值列表"""
        filter_obj, page_obj = self._parse_filter_and_page(data)
        result = self.resource_provider.list_attr_value(filter_obj, page_obj, **options)
        return result.to_dict()

    def list_instance(self, data: Dict, **options) -> Dict:
        """查询资源实例列表(支持分页)"""
        filter_obj, page_obj = self._parse_filter_and_page(data)
        result = self.resource_provider.list_instance(filter_obj, page_obj, **options)
        return result.to_dict()

    def fetch_instance_info(self, data: Dict, **options) -> List[Dict]:
        """查询资源实例列表"""
        filter_obj, _ = self._parse_filter_and_page(data)
        result = self.resource_provider.fetch_instance_info(filter_obj, **options)
        return result.to_list()

    def list_instance_by_policy(self, data: Dict, **options) -> List[Dict]:
        """根据策略表达式查询资源实例"""
        filter_obj, page_obj = self._parse_filter_and_page(data)
        result = self.resource_provider.list_instance_by_policy(filter_obj, page_obj, **options)
        return result.to_list()

    def search_instance(self, data: Dict, **options) -> Dict:
        """根据关键字查询资源实例"""
        filter_obj, page_obj = self._parse_filter_and_page(data)
        result = self.resource_provider.search_instance(filter_obj, page_obj, **options)
        return result.to_dict()

    def _parse_filter_and_page(self, data: Dict) -> Tuple[FancyDict, Page]:
        """处理请求参数"""
        filter_obj = get_filter_obj(
            data["filter"], ["ids", "parent", "search", "resource_type_chain", "keyword", "ancestors"]
        )
        page_obj = get_page_obj(data.get("page"))
        return filter_obj, page_obj
