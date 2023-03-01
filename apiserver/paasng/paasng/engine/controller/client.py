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
"""Client to communicate with controller
"""
import logging
from typing import Any, Dict, List

from blue_krill.auth.jwt import ClientJWTAuth, JWTAuthConf
from django.conf import settings
from requests.status_codes import codes

from paasng.utils.basic import get_requests_session
from paasng.utils.local import local

from .exceptions import BadResponse

logger = logging.getLogger(__name__)


class ControllerClient:
    """A Client for calling controller(workloads's system part) APIs"""

    _client_role = 'internal-sys'

    def __init__(self, controller_host: str, jwt_conf: JWTAuthConf):
        self.controller_host = controller_host
        jwt_conf.role = self._client_role
        self.auth_instance = ClientJWTAuth(jwt_conf)

    ################
    # Regular Path #
    ################
    def list_region_clusters(self, region):
        """List region clusters"""
        return self.request('GET', f'/regions/{region}/clusters/')

    def get_cluster_egress_info(self, region, cluster_name):
        """Get cluster's egress info"""
        return self.request('GET', f'/services/regions/{region}/clusters/{cluster_name}/egress_info/')

    def create_cnative_app_model_resource(self, region: str, data: Dict[str, Any]) -> Dict:
        """Create a cloud-native AppModelResource object

        :param region: Application region
        :param data: Payload for create resource
        """
        return self.request('POST', f'/regions/{region}/app_model_resources/', desired_code=codes.created, json=data)

    def app__delete(self, region, app_name):
        """"""
        return self.request(
            'DELETE',
            '/regions/{region}/apps/{name}'.format(region=region, name=app_name),
            desired_code=codes.no_content,
        )

    def app__retrive_by_name(self, region, app_name):
        """Retrieve an blueking app by uuid"""
        return self.request(
            'GET',
            '/regions/{region}/apps/{name}'.format(region=region, name=app_name),
        )

    def archive_app(self, region: str, app_name: str, operation_id: str):
        """Stop All Process of the app"""
        return self.request(
            'POST',
            '/regions/{region}/apps/{name}/archive/'.format(region=region, name=app_name),
            desired_code=codes.no_content,
            json={'operation_id': operation_id},
        )

    def interrupt_build_process(self, region: str, app_name: str, build_process_id: str):
        """Interrupt a running build process"""
        return self.request(
            'POST', f'/regions/{region}/apps/{app_name}/build_processes/{build_process_id}/interruptions/'
        )

    def builds__retrieve(self, region, app_name, limit=20, offset=0):
        return self.request(
            'GET',
            '/regions/{region}/apps/{name}/builds/'.format(region=region, name=app_name),
            params={
                'limit': limit,
                'offset': offset,
            },
        )

    def retrieve_app_config(self, region, app_name):
        """Retrieve an app's config"""
        return self.request(
            'GET',
            '/regions/{region}/apps/{name}/config/'.format(region=region, name=app_name),
        )

    def bind_app_cluster(self, region: str, app_name: str, cluster_name: str):
        """Bind App to given cluster"""
        return self.request(
            'POST',
            '/regions/{region}/apps/{name}/bind_cluster/{cluster_name}/'.format(
                region=region, name=app_name, cluster_name=cluster_name
            ),
            desired_code=codes.ok,
        )

    def get_process_instances(self, region, app_name, process_type):
        """Get process instance"""
        return self.request(
            'GET',
            '/regions/{region}/apps/{app_name}/process_types/{process_type}/instances/'.format(
                region=region, app_name=app_name, process_type=process_type
            ),
        )

    # Region Cluster State binding start

    def app_rcsbinding__create(self, region, app_name):
        return self.request('POST', f'/regions/{region}/apps/{app_name}/rcstate_binding/', desired_code=codes.created)

    def app_rcsbinding__destroy(self, region, app_name):
        return self.request('DELETE', f'/regions/{region}/apps/{app_name}/rcstate_binding/')

    # Region Cluster State binding end

    # Bk-App(module) related start

    def delete_module_related_res(self, app_code: str, module_name: str):
        """Delete module's related resources"""
        return self.request(
            'DELETE', f'/applications/{app_code}/modules/{module_name}/related_resources/', desired_code=204
        )

    # Bk-App(module) related end

    # App Domains start

    def app_domains__update(self, region, app_name, domains: List[Dict]):
        return self.request('PUT', f'/services/regions/{region}/apps/{app_name}/domains/', json={'domains': domains})

    # App Domains end

    # App subpaths start

    def update_app_subpaths(self, region: str, app_name: str, subpaths: List[Dict]):
        """Update application's default subpaths"""
        return self.request(
            'PUT', f'/services/regions/{region}/apps/{app_name}/subpaths/', json={'subpaths': subpaths}
        )

    # App subpaths end

    # Process Metrics Start
    def upsert_app_monitor(
        self,
        region: str,
        app_name: str,
        port: int,
        target_port: int,
    ):
        data = {
            "port": port,
            "target_port": target_port,
        }
        return self.request('POST', f'/regions/{region}/apps/{app_name}/metrics_monitor/', json=data)

    def app_proc_metrics__list(
        self,
        region,
        app_name,
        process_type,
        instance_name,
        metric_type,
        step,
        start_time=None,
        end_time=None,
        time_range_str=None,
    ):
        return self.request(
            'GET',
            f'/regions/{region}/apps/{app_name}/processes/{process_type}/instances/{instance_name}/metrics/',
            params={
                'metric_type': metric_type,
                'start_time': start_time,
                'end_time': end_time,
                'step': step,
                'time_range_str': time_range_str,
            },
        )

    def app_proc_all_metrics__list(
        self, region, app_name, process_type, metric_type, step, start_time=None, end_time=None, time_range_str=None
    ):
        return self.request(
            'GET',
            f'/regions/{region}/apps/{app_name}/processes/{process_type}/metrics/',
            params={
                'metric_type': metric_type,
                'start_time': start_time,
                'end_time': end_time,
                'step': step,
                'time_range_str': time_range_str,
            },
        )

    # Process Metrics End

    def get_swagger_docs(self):
        return self.request('GET', '/swagger.json')

    def request(self, method, path, desired_code=codes.ok, **kwargs):
        """Wrap request.request to provide auth header"""
        url = self.controller_host + path
        kwargs['headers'] = {settings.REQUEST_ID_HEADER_KEY: local.request_id}
        kwargs['auth'] = self.auth_instance
        logger.debug(f"Controller client sending request to [{method}]{url}, kwargs={kwargs}.")
        resp = get_requests_session().request(method, url, **kwargs)

        if resp.status_code == desired_code:
            try:
                return resp.json()
            except Exception:
                return resp

        raise BadResponse(resp)
