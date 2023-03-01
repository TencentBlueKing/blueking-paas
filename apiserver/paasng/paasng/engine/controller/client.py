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
from typing import TYPE_CHECKING, Any, Dict

from blue_krill.auth.jwt import ClientJWTAuth, JWTAuthConf
from django.conf import settings
from requests.status_codes import codes

from paas_wl.cluster.models import Cluster
from paas_wl.cluster.serializers import ClusterSLZ
from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.egress.models import RCStateAppBinding, RegionClusterState
from paasng.engine.controller.exceptions import BadResponse
from paasng.utils.basic import get_requests_session
from paasng.utils.local import local

if TYPE_CHECKING:
    from paas_wl.platform.applications.models import EngineApp


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
        return ClusterSLZ(data=Cluster.objects.filter(region=region), many=True).data

    def get_cluster_egress_info(self, region, cluster_name):
        """Get cluster's egress info"""
        from paas_wl.networking.egress.misc import get_cluster_egress_ips

        cluster = Cluster.objects.get(region=region, name=cluster_name)
        return get_cluster_egress_ips(cluster)

    def create_cnative_app_model_resource(self, region: str, data: Dict[str, Any]) -> Dict:
        """Create a cloud-native AppModelResource object

        :param region: Application region
        :param data: Payload for create resource
        :raises: ValidationError when CreateAppModelResourceSerializer validation failed
        """
        from paas_wl.cnative.specs.models import AppModelResource, create_app_resource
        from paas_wl.cnative.specs.serializers import AppModelResourceSerializer, CreateAppModelResourceSerializer

        serializer = CreateAppModelResourceSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        resource = create_app_resource(
            # Use Application code as default resource name
            name=d['code'],
            image=d['image'],
            command=d.get('command'),
            args=d.get('args'),
            target_port=d.get('target_port'),
        )
        model_resource = AppModelResource.objects.create_from_resource(
            region, d['application_id'], d['module_id'], resource
        )
        return AppModelResourceSerializer(model_resource).data

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

    def app_rcsbinding__create(self, wl_engine_app: 'EngineApp'):
        cluster = get_cluster_by_app(wl_engine_app)
        state = RegionClusterState.objects.filter(region=wl_engine_app.region, cluster_name=cluster.name).latest()
        RCStateAppBinding.objects.create(app=wl_engine_app, state=state)

    def app_rcsbinding__destroy(self, wl_engine_app: 'EngineApp'):
        binding = RCStateAppBinding.objects.get(app=wl_engine_app)
        # Update app scheduling config
        # TODO: Below logic is safe be removed as long as the node_selector will be fetched
        # dynamically by querying for binding state.
        latest_config = wl_engine_app.latest_config
        # Remove labels related with current binding
        for key in binding.state.to_labels():
            latest_config.node_selector.pop(key, None)
        latest_config.save()
        binding.delete()

    # Region Cluster State binding end

    # Bk-App(module) related start

    def delete_module_related_res(self, app_code: str, module_name: str):
        """Delete module's related resources"""
        return self.request(
            'DELETE', f'/applications/{app_code}/modules/{module_name}/related_resources/', desired_code=204
        )

    # Bk-App(module) related end

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
