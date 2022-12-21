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
"""API Gateway related functionalities"""
import logging
from typing import Collection, Dict, List, Optional, Tuple

from bkapi.bk_apigateway.client import Client
from bkapi_client_core.exceptions import BKAPIError, RequestException
from django.conf import settings
from typing_extensions import Protocol

from paasng.platform.applications.models import Application
from paasng.platform.oauth2.utils import get_oauth2_client_secret

from .exceptions import PluginApiGatewayServiceError
from .models import BkPluginDistributor

logger = logging.getLogger(__name__)


def safe_sync_apigw(plugin_app: Application):
    """Sync a plugin's API Gateway resource, ignore errors"""
    try:
        gw_service = PluginDefaultAPIGateway(plugin_app)
        id_ = gw_service.sync()
    except PluginApiGatewayServiceError:
        logger.exception('Unable to sync API Gateway resource for "%s"', plugin_app)
    else:
        plugin_app.bk_plugin_profile.mark_synced(id_, gw_service.gw_name)


def safe_update_gateway_status(plugin_app: Application, enabled: bool):
    """update a plugin's API Gateway status, ignore errors"""
    try:
        gw_service = PluginDefaultAPIGateway(plugin_app)
        gw_service.update_gateway_status(enabled)
    except PluginApiGatewayServiceError:
        logger.exception("Unable to update gateway status to %s for '%s'", enabled, plugin_app)


def set_distributors(plugin_app: Application, distributors: Collection[BkPluginDistributor]):
    """Set a plugin's distributors, this operation will update the related API Gateway permissions

    :raises: RuntimeError when operation fail to proceed
    """
    # Grant permissions: Check if plugin has related API Gateway resource first
    profile = plugin_app.bk_plugin_profile

    # Sync API Gateway resource on demand
    if not profile.is_synced:
        logger.info('Syncing api-gw resource for %s, triggered by setting distributor.', plugin_app)
        safe_sync_apigw(plugin_app)

    if not profile.api_gw_id:
        logger.error(
            'Unable to set distributor for "%s", no related API Gateway resource can be found', plugin_app.code
        )
        raise RuntimeError('no related API Gateway resource')

    old_distributors = set(plugin_app.distributors.all())
    distributors_set = set(distributors)
    to_added, to_removed = distributors_set - old_distributors, old_distributors - distributors_set

    # Perform grant, handle added distributors
    gw_service = PluginDefaultAPIGateway(plugin_app)
    for distributor in to_added:
        try:
            logger.info('Granting permissions on distributer: %s, plugin: %s', distributor, plugin_app)
            gw_service.grant(distributor)
        except PluginApiGatewayServiceError as e:
            raise RuntimeError(f'grant permissions error on {distributor}, detail: {e}')

    # Perform grant, handle removed distributors
    for distributor in to_removed:
        try:
            logger.info('Revoking permissions on distributer: %s, plugin: %s', distributor, plugin_app)
            gw_service.revoke(distributor)
        except PluginApiGatewayServiceError as e:
            raise RuntimeError(f'revoke permissions error on {distributor}, detail: {e}')

    # Modify records in database only when all previous actions finished
    plugin_app.distributors.set(distributors)


class PluginApiGWClient(Protocol):
    """Describes protocols of calling API Gateway management service"""

    def sync_api(self, *args, **kwargs) -> Dict:
        ...

    def grant_permissions(self, *args, **kwargs) -> Dict:
        ...

    def revoke_permissions(self, *args, **kwargs) -> Dict:
        ...

    def update_gateway_status(self, *args, **kwargs) -> Dict:
        ...


class PluginDefaultAPIGateway:
    """Manage the default BK API Gateway resource for a Plugin object, actions include
    "sync(create) gateway", "grant or revoke permissions of some plugin distributors" etc.

    :param plugin_app: the application object of plugin
    :param client: client object for calling API Gateway's management APIs, if not given, will
        generate a default one.
    """

    description_tmp = 'This gateway is related with bluking plugin: {plugin_code}, do not modify.'
    grant_dimension = 'api'

    def __init__(self, plugin_app: Application, client: Optional[PluginApiGWClient] = None):
        self.plugin_app = plugin_app
        self.client = client or self._make_api_client()
        self._user_auth_type = getattr(settings, 'BK_PLUGIN_APIGW_SERVICE_USER_AUTH_TYPE', 'default')
        self.set_gw_name()

    def set_gw_name(self):
        """Set the name of API Gateway resource, it will be used for later processing"""
        profile = self.plugin_app.bk_plugin_profile
        # When name is absent in plugin profile, generate a new name
        # WARN: The default value for gateway name should not exceeds 20 characters long.
        self.gw_name = profile.api_gw_name or f'bk-{self.plugin_app.code}'

    def sync(self) -> int:
        """Sync API gateway resource, if the gateway resource doesn't exist yet, create it.

        :returns: id of gateway resource
        :raise: PluginApiGatewayServiceError when unable to sync
        """
        # "bk_username" or "accessToken" is not required for calling "sync_api". When the API call was
        # succeeded, a new API Gateway will be created and it will be bound with given "bk_app_code".
        # If you want to make any further modifications to the API Gateway, the identical "bk_app_code"
        # must be provided.
        description = self.description_tmp.format(plugin_code=self.plugin_app.code)
        try:
            ret = self.client.sync_api(
                path_params={'api_name': self.gw_name},
                data={
                    "name": self.gw_name,
                    'description': description,
                    'maintainers': self._get_maintainers(),
                    'user_auth_type': self._user_auth_type,
                    # Make it public and available by setting "status" and "is_public"
                    'status': 1,
                    'is_public': True,
                },
            )
        except (RequestException, BKAPIError) as e:
            raise PluginApiGatewayServiceError(f'sync gateway resource error, detail: {e}')
        return ret['data']['id']

    def grant(self, distributor: BkPluginDistributor):
        """Grant permissions on given distributor

        :raise: PluginApiGatewayServiceError when unable to grant permissions
        """
        try:
            self.client.grant_permissions(
                path_params={'api_name': self.gw_name},
                data={"target_app_code": distributor.bk_app_code, 'grant_dimension': self.grant_dimension},
            )
        except (RequestException, BKAPIError) as e:
            raise PluginApiGatewayServiceError(f'grant permissions error, detail: {e}')

    def revoke(self, distributor: BkPluginDistributor):
        """Revoke permissions on given distributor

        :raise: PluginApiGatewayServiceError when unable to revoke permissions
        """
        try:
            self.client.revoke_permissions(
                path_params={'api_name': self.gw_name},
                # INFO: "revoke" supports plural form: "target_app_codes" while "grant" only allows a single
                # "target_app_code"
                data={"target_app_codes": [distributor.bk_app_code], 'grant_dimension': self.grant_dimension},
            )
        except (RequestException, BKAPIError) as e:
            raise PluginApiGatewayServiceError(f'revoke permissions error, detail: {e}')

    def update_gateway_status(self, enabled: bool):
        """Update gateway status to enabled or not

        :raise: PluginApiGatewayServiceError when unable to update gateway status
        """
        try:
            self.client.update_gateway_status(
                path_params={'api_name': self.gw_name}, data={"status": 1 if enabled else 0}
            )
        except (RequestException, BKAPIError) as e:
            raise PluginApiGatewayServiceError(f"update gateway status error, detail: {e}")

    def _get_maintainers(self) -> List[str]:
        """Get plugin's maintainer list"""
        return self.plugin_app.get_developers()

    def _make_api_client(self) -> PluginApiGWClient:
        """Make a client object for requesting"""
        client = Client(endpoint=settings.BK_API_URL_TMPL, stage=settings.BK_PLUGIN_APIGW_SERVICE_STAGE)
        bk_app_code, bk_app_secret = self._get_credentials()
        client.update_bkapi_authorization(bk_app_code=bk_app_code, bk_app_secret=bk_app_secret)
        return client.api

    def _get_credentials(self) -> Tuple[str, str]:
        """Get the application's (code, secret) pair"""
        secret = get_oauth2_client_secret(self.plugin_app.code, self.plugin_app.region)
        return self.plugin_app.code, secret
