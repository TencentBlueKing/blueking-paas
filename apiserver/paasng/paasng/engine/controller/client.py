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
from typing import Any, Dict, List, Optional

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

    def app__create(self, region, app_name, app_type):
        """Retrieve an blueking app by uuid"""
        return self.request(
            'POST',
            '/regions/{region}/apps/'.format(region=region),
            desired_code=codes.created,
            json={'name': app_name, 'type': app_type},
        )

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

    def app__release(
        self,
        region: str,
        app_name: str,
        build_id: str,
        deployment_id: Optional[str],
        extra_envs: Dict[str, str],
        procfile: Dict[str, str],
    ):
        """Deploy a build slug"""
        return self.request(
            'POST',
            '/regions/{region}/apps/{name}/releases/'.format(region=region, name=app_name),
            desired_code=codes.created,
            json={'build': build_id, 'deployment_id': deployment_id, 'extra_envs': extra_envs, 'procfile': procfile},
        )

    def get_app_release(self, region, app_name, release_id):
        """Deploy a build slug"""
        return self.request(
            'GET',
            '/regions/{region}/apps/{name}/releases/'.format(region=region, name=app_name),
            json={
                'release_id': release_id,
            },
        )

    def get_app_build(self, region, app_name, build_id):
        """Get the build object by id"""
        return self.request(
            'GET',
            '/regions/{region}/apps/{name}/builds/{build_id}'.format(region=region, name=app_name, build_id=build_id),
        )

    def app__build_processes(
        self,
        region,
        app_name,
        source_tar_path,
        branch,
        revision,
        stream_channel_id,
        procfile,
        extra_envs=None,
        image=None,
        buildpacks=None,
    ):
        return self.request(
            'POST',
            '/regions/{region}/apps/{name}/build_processes/'.format(region=region, name=app_name),
            desired_code=codes.created,
            json={
                'source_tar_path': source_tar_path,
                'branch': branch,
                'revision': revision,
                'stream_channel_id': stream_channel_id,
                'procfile': procfile,
                'extra_envs': extra_envs,
                'image': image,
                'buildpacks': buildpacks,
            },
        )

    def read_build_process_result(self, region: str, app_name: str, build_process_id: str):
        return self.request(
            'GET',
            '/regions/{region}/apps/{name}/build_processes/{build_process_id}/result'.format(
                region=region, name=app_name, build_process_id=build_process_id
            ),
        )

    def interrupt_build_process(self, region: str, app_name: str, build_process_id: str):
        """Interrupt a running build process"""
        return self.request(
            'POST', f'/regions/{region}/apps/{app_name}/build_processes/{build_process_id}/interruptions/'
        )

    def app__run_command(
        self,
        region: str,
        app_name: str,
        build_id: str,
        command: str,
        stream_channel_id: str,
        operator: str,
        type_: str,
        extra_envs: dict,
    ):
        return self.request(
            'POST',
            f'/regions/{region}/apps/{app_name}/commands/',
            desired_code=codes.created,
            json={
                'build': build_id,
                'command': command,
                'stream_channel_id': stream_channel_id,
                'operator': operator,
                'type': type_,
                'extra_envs': extra_envs,
            },
        )

    def command__retrieve(self, region: str, app_name: str, command_id: str):
        return self.request(
            'GET',
            f'/regions/{region}/apps/{app_name}/commands/{command_id}',
        )

    def list_processes_specs(self, region: str, app_name: str):
        """List specs of app's all processes"""
        return self.request('GET', f'/regions/{region}/apps/{app_name}/processes/specs/')

    def sync_processes_specs(self, region: str, app_name: str, processes: List[Dict]):
        """Sync specs of app's all processes by processes"""
        return self.request(
            'POST',
            f'/regions/{region}/apps/{app_name}/processes/specs/',
            json={"processes": processes},
            desired_code=codes.no_content,
        )

    def list_processes_statuses(self, region: str, app_name: str):
        """List current statuses of app's all processes"""
        return self.request('GET', f'/regions/{region}/apps/{app_name}/processes/')

    def create_build(self, region, app_name, procfile: Dict[str, str], env_variables: Dict[str, str]):
        """Create the **fake** build for Image Type App"""
        return self.request(
            'POST',
            '/regions/{region}/apps/{name}/builds/placeholder/'.format(region=region, name=app_name),
            json={
                "procfile": procfile,
                "env_variables": env_variables,
            },
            desired_code=codes.created,
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

    def update_app_config(self, region, app_name, payload):
        """Patch app config"""
        return self.request(
            'POST',
            '/regions/{region}/apps/{name}/config/'.format(region=region, name=app_name),
            desired_code=codes.created,
            json=payload,
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

    def update_app_metadata(self, region, app_name, payload):
        """Patch app config"""
        return self.request(
            'POST',
            '/regions/{region}/apps/{name}/config/metadata'.format(region=region, name=app_name),
            json=payload,
        )

    def upsert_image_credentials(self, region, app_name, credentials):
        """upsert app's image credentials"""
        return self.request(
            'POST',
            f"/regions/{region}/apps/{app_name}/image_credentials/",
            desired_code=codes.ok,
            json=credentials,
        )

    def create_webconsole(
        self, region, app_name, process_type, process_instance, operator, container_name=None, command="bash"
    ):
        """Create WebConsole"""
        return self.request(
            'POST',
            f'/regions/{region}/apps/{app_name}/processes/{process_type}/instances/{process_instance}/webconsole/',
            json={"container_name": container_name, "operator": operator, "command": command},
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

    # Process Services start

    def app_proc_ingress_actions__sync(self, region, app_name):
        return self.request('POST', f'/services/regions/{region}/apps/{app_name}/proc_ingresses/actions/sync')

    # Process Services end

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
