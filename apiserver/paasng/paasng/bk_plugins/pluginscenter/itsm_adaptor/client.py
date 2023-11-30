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
import json
import logging
from pathlib import Path
from typing import List, Optional

from bkapi_client_core.exceptions import APIGatewayResponseError
from django.conf import settings

from paasng.bk_plugins.pluginscenter.itsm_adaptor.apigw.client import Client
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ApprovalServiceName
from paasng.bk_plugins.pluginscenter.itsm_adaptor.exceptions import (
    ItsmApiError,
    ItsmCatalogNotExistsError,
    ItsmGatewayServiceError,
    ItsmServiceNotExistsError,
)
from paasng.bk_plugins.pluginscenter.models.instances import ItsmDetail
from paasng.infras.iam.apigw.client import Group as ItsmGroup

# from paasng.bk_plugins.pluginscenter.thirdparty.utils import registry_i18n_hook

logger = logging.getLogger(__name__)


class ItsmClient:
    """bk-itsm 通过 API 网关提供的 API"""

    def __init__(self, login_cookie: Optional[str] = ""):
        # 在 itsm 上注册的服务目录
        self.catalog_name = "插件开发者中心"
        self.login_cookie_name = settings.BK_COOKIE_NAME

        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_PLUGIN_APIGW_SERVICE_STAGE)
        client.update_bkapi_authorization(
            **{
                "bk_app_code": settings.BK_APP_CODE,
                "bk_app_secret": settings.BK_APP_SECRET,
                self.login_cookie_name: login_cookie,
            }
        )
        # 处理国际化
        # registry_i18n_hook(client.session)
        self.client: ItsmGroup = client.api

    def search_service_catalogs(self) -> dict:
        """查找服务目录"""
        try:
            resp = self.client.get_service_catalogs(
                data={},
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(f"get service catalogs from itsm error: {e}")

        if resp.get("code") != 0:
            logger.exception(f"search service catalogs from itsm error, message:{resp}")
            raise ItsmApiError(resp["message"])
        return resp.get("data", {})

    def get_root_catalog_id(self) -> int:
        """获取根目录ID"""
        catalogs = self.search_service_catalogs()
        for d in catalogs:
            # key=='root' && level==0 则为根目录
            if d["key"] == "root" and d["level"] == 0:
                return d["id"]

        # 如果没有找到根目录抛出异常
        logger.exception(f"the root catalog information cannot be queried from itsm, catalogs: {catalogs}")
        raise ItsmCatalogNotExistsError("the root catalog information cannot be queried from itsm")

    def get_plugin_center_catalog_id(self) -> int:
        """获取插件开发者中心的服务目录ID

        Itsm API 只支持通过 service_key 过滤服务目录，无法通过服务名精确查询到指定的服务
        """
        catalogs = self.search_service_catalogs()
        for d in catalogs:
            # key=='root' && level==0 则为根目录
            if d["key"] == "root" and d["level"] == 0:
                # 从根目录的二级目录(children)中根据 name 匹配过滤，根目录下的服务目录名一定是唯一的
                for c in d["children"]:
                    if c["name"] == self.catalog_name:
                        return c["id"]

        # 如果没有找到根目录抛出异常
        logger.exception(f"the plugin_center catalog information cannot be queried from itsm, catalogs: {catalogs}")
        raise ItsmCatalogNotExistsError("the plugin_center catalog information cannot be queried from itsm")

    def create_plugin_center_catalog(self, root_catalog_id: int) -> int:
        """给插件开发者中心创建独立的服务目录，父目录为根目录"""
        data = {
            "parent__id": root_catalog_id,
            "name": self.catalog_name,
            "project_key": "0",
            "desc": "",
        }
        try:
            resp = self.client.create_service_catalog(
                data=data,
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(f"create plugin_center catalog at itsm error: {e}")

        if resp.get("code") != 0:
            logger.exception(f"create plugin_center catalog at itsm error, message:{resp} \ndata: {data}")
            raise ItsmApiError(resp["message"])

        # 返回“插件开发者中心”的服务目录 ID
        return resp.get("data", {}).get("id")

    def get_service_id_by_name(self, catalog_id: int, service_name: str) -> int:
        """查询指定目录下, 服务名对应的服务ID"""
        try:
            resp = self.client.get_services(
                data={"catalog_id": catalog_id},
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(
                f"Failed to query the services under the catalog(id:{catalog_id}) on itsm error: {e}"
            )

        if resp.get("code") != 0:
            logger.exception(f"Failed to query the services under the catalog(id:{catalog_id}) on itsm error:{resp}")
            raise ItsmApiError(resp["message"])

        resp_data = resp.get("data", {})
        service_dict = {d["name"]: d["id"] for d in resp_data}

        # itsm 中返回的服务名是中文名
        service_id = service_dict.get(ApprovalServiceName.get_choice_label(service_name))
        if not service_id:
            raise ItsmServiceNotExistsError(f"There is no service({service_name}) in itsm's catalog(id: {catalog_id})")
        return service_id

    def import_service(self, catalog_id: int, service_name: str) -> int:
        """导入流程服务"""
        service_path = Path(settings.BASE_DIR) / "support-files" / "itsm" / f"plugins_{service_name}.json"
        with open(service_path, "r", encoding="utf-8") as f:
            service_data = json.loads(f.read())

        # 流程数据中添加要导入的服务目录ID信息
        service_data["catalog_id"] = catalog_id
        try:
            resp = self.client.import_service(
                data=service_data,
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(f"import service({service_path}) to itsm error: {e}")

        resp_code = resp.get("code")
        if resp_code == 3900035:
            # 3900035 代表服务已经在 itsm 上存在，则直接从 itsm 上查询服务 id
            service_id = self.get_service_id_by_name(catalog_id, service_name)
            return service_id

        if resp_code != 0:
            logger.exception(f"import service({service_path}) to itsm error, message:{resp}")
            raise ItsmApiError(resp["message"])

        # 返回导入的服务ID
        return resp.get("data", {}).get("id")

    def create_ticket(self, service_id: int, creator: str, callback_url: str, fields: List[dict]) -> ItsmDetail:
        """创建申请单据"""
        data = {
            "service_id": service_id,
            "creator": creator,
            "fields": fields,
            "meta": {
                # 单据结束的时候，itsm 会调用 callback_url 告知审批结果
                "callback_url": callback_url,
            },
        }
        try:
            resp = self.client.create_ticket(
                data=data,
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(f"create application ticket at itsm  error: {e}")

        if resp.get("code") != 0:
            logger.exception(f"create application ticket at itsm  error, message:{resp} \ndata: {data}")
            raise ItsmApiError(resp["message"])

        # 返回创建流程的单号
        resp_data = resp.get("data", {})
        return ItsmDetail(fields=fields, sn=resp_data.get("sn", ""), ticket_url=resp_data.get("ticket_url", ""))

    def get_ticket_status(self, sn: str) -> dict:
        try:
            resp = self.client.get_ticket_status(
                data={
                    "sn": sn,
                },
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(f"get application ticket status from itsm error: {e}")

        if resp.get("code") != 0:
            logger.exception(f"get application ticket status from itsm error, message:{resp} \nsn: {sn}")
            raise ItsmApiError(resp["message"])

        # 返回单据详情
        return resp.get("data", {})

    def withdraw_ticket(self, sn: str, action_type: str, operator: str) -> bool:
        """撤销单据"""
        data = {
            "sn": sn,
            # 单据处理人，必须在处理人范围内
            "operator": operator,
            "action_type": "WITHDRAW",
            "action_message": "applicant withdraw ticket",
        }
        try:
            resp = self.client.operate_ticket(
                data=data,
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(f"withdraw application ticket status from itsm error: {e}")

        if resp.get("code") != 0:
            logger.exception(f"withdraw application ticket status from itsm error, message:{resp} \ndata: {data}")
            raise ItsmApiError(resp["message"])

        # 是否操作成功
        return resp.get("result")

    def verify_token(self, token: str) -> bool:
        """验证回调链接中返回的 token
        注意: 该 API 需要验证用户登录态
        """
        try:
            resp = self.client.token_verify(
                data={"token": token},
            )
        except APIGatewayResponseError as e:
            raise ItsmGatewayServiceError(f"verify token from itsm error: {e}")

        if resp.get("code") != 0:
            logger.exception(f"verify token from itsm error, resp:{resp} \ntoken: {token}")
            raise ItsmApiError(resp["message"])

        if not (is_passed := resp.get("data", {}).get("is_passed")):
            logging.exception(f"itsm token checksum fails, resp:{resp} \ntoken: {token}")

        return is_passed
