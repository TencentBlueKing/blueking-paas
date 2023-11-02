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
"""kres is a well capsuled package for playing with kubernetes resources
"""
import functools
import json
import logging
import time
from contextlib import contextmanager
from enum import Enum
from types import ModuleType
from typing import Any, Callable, Collection, Dict, Iterator, List, Optional, Tuple, Type, Union, overload

import cattr
from attrs import define
from kubernetes import client as client_mod
from kubernetes.client.api_client import ApiClient
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic.exceptions import ResourceNotFoundError
from kubernetes.dynamic.resource import Resource, ResourceInstance

from paas_wl.infras.resources.base.constants import QUERY_LOG_DEFAULT_TIMEOUT
from paas_wl.infras.resources.base.exceptions import (
    CreateServiceAccountTimeout,
    ReadTargetStatusTimeout,
    ResourceDeleteTimeout,
    ResourceMissing,
)
from paas_wl.infras.resources.base.kube_client import CoreDynamicClient
from paas_wl.utils.kubestatus import parse_pod

logger = logging.getLogger(__name__)

# Typing alias
Namespace = Optional[str]
Manifest = Union[Dict[str, Any], ResourceInstance]

ClientOptionsDict = Dict[str, Optional[Union[float, int]]]

_default_options: ClientOptionsDict = {}


def get_default_options():
    """default_options is the default options for whole kres module"""
    return _default_options


def set_default_options(options: ClientOptionsDict):
    global _default_options
    _default_options = options


class PatchType(str, Enum):
    """Different merge types when patching a kubernetes resource
    See also: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/update-api-object-kubectl-patch/
    """

    JSON = 'json'
    MERGE = 'merge'
    STRATEGIC = 'strategic'

    def to_content_type(self):
        """Get header value when used in "Content-Type" """
        ct = {
            PatchType.JSON: 'application/json-patch+json',
            PatchType.MERGE: 'application/merge-patch+json',
            PatchType.STRATEGIC: 'application/strategic-merge-patch+json',
        }
        return ct[self]


@contextmanager
def wrap_missing_exc(namespace: Namespace, name: str):
    """A context manager which transform exc into ResourceMissing automatically"""
    try:
        yield
    except ApiException as e:
        if e.status == 404:
            raise ResourceMissing(namespace=namespace, name=name)
        raise


class KubeObjectList:
    """Handle List object returned by kubernetes client"""

    def __init__(self, obj: ResourceInstance):
        self.obj = obj
        self.metadata = obj.metadata

        # Make a List of `ResourceInstance` objects instead of original `ResourceField`
        self.items: List[ResourceInstance] = []
        for item in self.obj.items:
            self.items.append(ResourceInstance(self.obj.client, item))


class NameBasedMethodProxy:
    """A descriptor which proxy method calls to `self.ops_name`"""

    def __set_name__(self, owner, name: str):
        self.method_name = name

    @overload
    def __get__(self, instance: None, owner: None) -> 'NameBasedMethodProxy':
        ...

    @overload
    def __get__(self, instance: object, owner: Type) -> Callable:
        ...

    def __get__(self, instance, owner: Optional[Type] = None) -> Union['NameBasedMethodProxy', Callable]:
        if not instance:
            return self
        return getattr(instance.ops_name, self.method_name)


class BaseKresource:
    """Base class for kubernetes resource utils

    :param client: Kubernetes client object
    :param request_timeout: timeout in seconds
    :param api_version: Specify an api_version, otherwise use "preferred" version instead
    """

    kind = ''

    def __init__(self, client, request_timeout: Optional[float] = None, api_version: str = ''):
        # Kres is able to support both client module or an ApiClient instance
        if isinstance(client, ModuleType):
            # The ApiClient will use the default Configuration by default
            _api_client = ApiClient()
        elif isinstance(client, ApiClient):
            _api_client = client
        else:
            raise TypeError(f"'client' is not a valid client type, current type: {type(client)}")

        self.client = _api_client

        # TODO: Add cache
        self.dynamic_client = CoreDynamicClient(self.client)
        self.version = self.dynamic_client.version

        self.request_timeout = request_timeout or get_default_options().get("request_timeout")
        self.api_version = api_version
        self.ops_name = NameBasedOperations(self, self.request_timeout)
        self.ops_label = LabelBasedOperations(self, self.request_timeout)

    # Make shortcuts: proxy a collection of methods to self.ops_name(name
    # based operations) for convenience.
    get_preferred_version = NameBasedMethodProxy()
    get_available_versions = NameBasedMethodProxy()
    get = NameBasedMethodProxy()
    patch = NameBasedMethodProxy()
    replace_or_patch = NameBasedMethodProxy()
    create_or_update = NameBasedMethodProxy()
    get_or_create = NameBasedMethodProxy()
    create = NameBasedMethodProxy()
    delete = NameBasedMethodProxy()
    update_subres = NameBasedMethodProxy()
    patch_subres = NameBasedMethodProxy()
    update_status = NameBasedMethodProxy()

    @classmethod
    def clone_from(cls, obj: 'BaseKresource') -> 'BaseKresource':
        """Clone a Kres object from another"""
        return cls(obj.client, obj.request_timeout)


class BaseOperations:
    """Base operation class for kubernetes resources

    :param client: Kubernetes client instance
    :param kres: KResource object bind
    :param request_timeout: default request timeout
    """

    def __init__(self, kres: BaseKresource, request_timeout: float):
        # self.client = client
        self.client = kres.dynamic_client
        self.kres = kres
        self.request_timeout = request_timeout

        self._available_resources = self.client.resources.search(kind=self.kres.kind)
        try:
            self._preferred_resource = self.client.get_preferred_resource(self.kres.kind)
        except ResourceNotFoundError:
            # 存在一种场景，即某类资源在 preferred group version 中是不存在的，
            # 但集群中存在，此时如果指定 api_version 进行访问 / 操作，应当是被允许的
            if not (self._available_resources and self.kres.api_version):
                raise

            self._preferred_resource = None

        self.resource: Resource  # make type checker happy
        if not self.kres.api_version:
            self.resource = self._preferred_resource
        else:
            # A specified api_version was given
            self.resource = self.client.resources.get(kind=self.kres.kind, api_version=self.kres.api_version)

    def get_preferred_version(self) -> str:
        if not self._preferred_resource:
            return ''

        return self._preferred_resource.group_version

    def get_available_versions(self) -> List[str]:
        return [r.group_version for r in self._available_resources]

    @property
    def default_kwargs(self) -> Dict[str, Union[str, float]]:
        """The default request kwargs"""
        if self.request_timeout:
            return {'timeout_seconds': self.request_timeout}
        else:
            return {}


class NameBasedOperations(BaseOperations):
    """All operations in this class are based on resource name"""

    def get(self, name: str, namespace: Namespace = None) -> ResourceInstance:
        """Get a resource by name

        :param name: Resource name
        :param namespace: Resource namespace, only required for is_namespaced resource
        :raises: ResourceMissing when resource can not be found
        """
        with wrap_missing_exc(namespace, name):
            return self.resource.get(name=name, namespace=namespace, **self.default_kwargs)

    def patch(
        self, name: str, body: Manifest, namespace: Namespace = None, ptype: PatchType = PatchType.STRATEGIC, **kwargs
    ) -> ResourceInstance:
        """Patch a resource by name

        :param ptype: Patch type, default to "strategic"
        :return: Updated instance
        :raises: ResourceMissing when resource can not be found
        """
        extra_kwargs = self.default_kwargs.copy()
        extra_kwargs.update(kwargs)
        extra_kwargs['content_type'] = ptype.to_content_type()

        with wrap_missing_exc(namespace, name):
            obj = self.resource.patch(name=name, body=body, namespace=namespace, **extra_kwargs)
        return obj

    def replace_or_patch(
        self, name: str, body: Manifest, namespace: Namespace = None, update_method: str = "replace", **kwargs
    ) -> ResourceInstance:
        """replace or patch a resource by name

        :return: Updated instance
        :raises: ResourceMissing when resource can not be found
        """
        assert update_method in ["replace", "patch"], "Invalid update_method {}".format(update_method)
        extra_kwargs = self.default_kwargs.copy()
        extra_kwargs.update(kwargs)

        with wrap_missing_exc(namespace, name):
            # Call replace/patch method
            _func = getattr(self.resource, update_method)
            obj = _func(name=name, body=body, namespace=namespace, **extra_kwargs)
        return obj

    def create_or_update(
        self,
        name: str,
        namespace: Namespace = None,
        body: Optional[Manifest] = None,
        update_method: str = "replace",
        content_type: Optional[str] = None,
        auto_add_version: bool = False,
    ) -> Tuple[ResourceInstance, bool]:
        """Create or update a resource by name

        :param content_type: content_type header for patch/replace requests
        :param auto_add_version: 当 update_method=replace 时，是否自动添加 metadata.resourceVersion 字段，默认为 False
        :returns: (instance, created)
        """
        assert update_method in ["replace", "patch"], "Invalid update_method {}".format(update_method)
        # Set a default body if body is not given
        if not body:
            body_dict: Dict = {'kind': self.kres.kind, 'metadata': {'name': name}}
        else:
            body_dict = self.client.serialize_body(body)

        body_dict.setdefault('kind', self.kres.kind)
        if body_dict and body_dict['metadata']['name'] != name:
            raise ValueError("name in args must match name in body")
        # Try call create method first
        try:
            obj = self.resource.create(body=body_dict, namespace=namespace, **self.default_kwargs)
            return obj, True
        except ApiException as e:
            # Only continue when resource is already exits
            if not (e.status == 409 and json.loads(e.body)["reason"] == "AlreadyExists"):
                raise

        if update_method == "replace" and auto_add_version:
            self._add_resource_version(name, namespace, body_dict)

        logger.info(f"Create {self.kres.kind} {name} failed, already existed, continue update")
        # Call replace/patch method
        _func = getattr(self.resource, update_method)
        update_kwargs = self.default_kwargs.copy()
        if content_type:
            update_kwargs['content_type'] = content_type
        obj = _func(name=name, body=body_dict, namespace=namespace, **update_kwargs)
        return obj, False

    def get_or_create(
        self, name: str, namespace: Namespace = None, body: Optional[Manifest] = None
    ) -> Tuple[ResourceInstance, bool]:
        """Get or create a resource

        :param name: name(primary key) of a kubernetes resource
        :param namespace: namespace of a kubernetes resource
        :returns: (instance, created)
        """
        try:
            obj = self.get(name, namespace=namespace)
            return obj, False
        except ResourceMissing:
            pass

        # Set a default body if body is not given
        if not body:
            body = {'kind': self.kres.kind, 'metadata': {'name': name}}

        logger.info("Unable to find %s %s, start creating.", self.kres.kind, name)
        instance = self.resource.create(body=body, namespace=namespace, **self.default_kwargs)
        return instance, True

    def create(self, name: str, body: Manifest, namespace: Namespace = None) -> ResourceInstance:
        """Create a resource

        :param name: name(primary key) of a kubernetes resource
        :param namespace: namespace of a kubernetes resource
        :returns: instance
        """
        logger.info("Creating %s %s.", self.kres.kind, name)
        body.setdefault('kind', self.kres.kind)
        instance = self.resource.create(body=body, namespace=namespace, **self.default_kwargs)
        return instance

    def delete(
        self,
        name: str,
        namespace: Optional[str] = None,
        raise_if_non_exists: bool = False,
        non_grace_period: bool = False,
        grace_period_seconds: Optional[int] = None,
    ):
        """Delete a resource if exists

        :param name: name(primary key) of a kubernetes resource
        :param namespace: namespace of a kubernetes resource
        :param raise_if_non_exists: raise if resource does not exists, default to False
        :param non_grace_period: set grace_period to 0, default to False
        :param grace_period_seconds: when this parameter is given and `non_grace_period` is False, set
            DeleteOptions using this value.
        """
        request_kwargs = self.default_kwargs
        body = DeleteOptions()
        if non_grace_period:
            request_kwargs.update(grace_period_seconds=0)
            body.grace_period_seconds = 0
        elif grace_period_seconds:
            request_kwargs.update(grace_period_seconds=grace_period_seconds)
            body.grace_period_seconds = grace_period_seconds

        resource = self.kres.dynamic_client.get_preferred_resource(self.kres.kind)
        try:
            resource.delete(name=name, body=cattr.unstructure(body), namespace=namespace, **request_kwargs)
        except ApiException as e:
            if e.status == 404:
                if raise_if_non_exists:
                    raise ResourceMissing(namespace=namespace, name=name) from e
                logger.warning("Delete failed, resource %s %s does not exists anymore", self.kres.kind, name)
                return
            raise

        logger.info("Resource %s %s has been deleted", self.kres.kind, name)

    def update_subres(
        self, subres_name: str, name: str, body: Manifest, namespace: Namespace = None
    ) -> ResourceInstance:
        """Update a subResources, such as Pod's Status.

        :param subres_name: name of subResource
        :return: Updated instance
        :raises: ResourceMissing when resource can not be found
        """
        sub_res = self.resource.subresources[subres_name]
        with wrap_missing_exc(namespace, name):
            obj = sub_res.replace(name=name, body=body, namespace=namespace, **self.default_kwargs)
        return obj

    def patch_subres(
        self,
        subres_type: str,
        name: str,
        body: Manifest,
        namespace: Namespace = None,
        ptype: PatchType = PatchType.STRATEGIC,
    ) -> ResourceInstance:
        """Patch a subResources, such as Pod's Status."""
        sub_res = self.resource.subresources[subres_type]
        with wrap_missing_exc(namespace, name):
            obj = sub_res.patch(
                name=name, body=body, namespace=namespace, content_type=ptype.to_content_type(), **self.default_kwargs
            )
        return obj

    def update_status(self, *args, **kwargs) -> ResourceInstance:
        """Update a resource's status field"""
        return functools.partial(self.update_subres, 'status')(*args, **kwargs)

    def _add_resource_version(self, name: str, namespace: Namespace, body_dict: dict):
        """get resource from k8s, and set metadata.resourceVersion to body_dict

        :raises: ResourceMissing when resource can not be found.
        """
        obj = self.get(name, namespace)
        body_dict['metadata'].setdefault('resourceVersion', obj.metadata.resourceVersion)


class LabelBasedOperations(BaseOperations):
    """All operations in this class are based on labels"""

    def list(self, labels: Dict, namespace: Namespace = None) -> KubeObjectList:
        """list resources by labels

        :param labels: labels dict
        :param namespace: Resource namespace, only required for is_namespaced resource
        :returns: Various kinds of kubernetes lists
        """
        list_resp = self.resource.get(
            label_selector=self.make_labels_string(labels), namespace=namespace, **self.default_kwargs
        )
        return KubeObjectList(list_resp)

    def delete_collection(self, labels: Dict[str, str], namespace: Namespace = None):
        """delete resources by labels"""
        labels_str = self.make_labels_string(labels)
        self.resource.delete_anyway(label_selector=labels_str, namespace=namespace, **self.default_kwargs)

    def delete_individual(self, labels: Dict[str, str], namespace: Namespace = None, non_grace_period: bool = False):
        """delete resources by labels, use a different approach by list the resources first, then
        delete it one by one.
        """
        # Reference to NameBasedOperations
        name_ops = NameBasedOperations(self.kres, self.request_timeout)
        for item in self.list(labels, namespace=namespace).items:
            name_ops.delete(item.metadata.name, namespace=namespace, non_grace_period=non_grace_period)

    def create_watch_stream(self, labels: Dict, namespace: Namespace = None, **kwargs) -> Iterator:
        """Create a stream object to watch changes

        :param int timeout_seconds/timeout: the total timeout for this watch request
        """
        kwargs = {**self.default_kwargs, **kwargs}
        # be compatible with timeout_seconds parameter
        kwargs.setdefault('timeout', kwargs.pop('timeout_seconds', None))
        return self.resource.watch(label_selector=self.make_labels_string(labels), namespace=namespace, **kwargs)

    @staticmethod
    def make_labels_string(labels: Dict) -> str:
        """Turn a labels dict into string format

        :param labels: dict of labels
        """
        return ",".join("{}={}".format(key, value) for key, value in labels.items())


# Individual resource types start


class KNode(BaseKresource):
    kind = 'Node'


class KNamespace(BaseKresource):
    kind = 'Namespace'

    def wait_for_default_sa(self, namespace: Namespace, timeout: Optional[float] = None, check_period: float = 0.5):
        """Calling this function will blocks until the default ServiceAccount was created

        :param timeout: timeout seconds for this join operation, default to never timeout
        :param check_period: wait interval for polling
        :raises: CreateServiceAccountTimeout if sa unable to appears in given timeout
        """
        time_started = time.time()
        while timeout is None or time.time() - time_started < timeout:
            if self.default_sa_exists(namespace):
                return None

            logger.warning("No default ServiceAccount found in namespace %s", namespace)
            time.sleep(check_period)

        raise CreateServiceAccountTimeout(namespace=namespace, timeout=timeout)

    def wait_until_removed(
        self,
        namespace: Namespace,
        timeout: float = 60,
        check_period: float = 0.5,
        raise_timeout: bool = False,
    ):
        """Calling this function will blocks until the given namespace was deleted

        :param timeout: timeout seconds for this join operation
        :param check_period: wait interval for polling
        :param raise_timeout: whether to throw an exception when timeout.
        :raises: ResourceDeleteTimeout if the namespace is still exists in given timeout and raise_timeout is True
        """
        now = time.time()
        when_timeout = now + timeout
        while now < when_timeout:
            now = time.time()
            try:
                self.get(namespace)
            except ResourceMissing:
                return True
            time.sleep(check_period)
        if raise_timeout:
            raise ResourceDeleteTimeout(resource_type=self.kind, namespace=namespace, name='')

    def default_sa_exists(self, namespace: Namespace) -> bool:
        """Check if a namespace has default ServiceAccount or not, this account was usually created
        by namespace controller which lives in controller manager.

        :returns: bool
        """
        try:
            KServiceAccount.clone_from(self).get('default', namespace=namespace)
        except ResourceMissing:
            return False

        # Q：为什么不再检查 ServiceAccount 绑定的 Secrets 信息
        # A：目前蓝鲸应用并没有使用 ServiceAccount 绑定的权限访问其他集群资源的需求，
        #    之前对 SA 的 Secrets 进行检查，主要目的是确保默认的 SA 已经初始化完成，避免应用 Pod 调度失败。
        #    但是在 k8s 1.24+ 版本中，命名空间在创建后并不会默认为 default SA 绑定 Secret（Token），
        #    该行为不会影响应用的正常部署，且此处检查 Secret 不再有意义，因此调整为仅检查 SA 是否存在。
        # Ref：
        #   1. https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.24.md#urgent-upgrade-notes
        #      keyword: LegacyServiceAccountTokenNoAutoGeneration
        #   2. https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.27/#serviceaccount-v1-core
        return True


class KReplicaSet(BaseKresource):
    kind = 'ReplicaSet'


class KPod(BaseKresource):
    kind = 'Pod'

    def wait_for_status(
        self,
        name: str,
        target_statuses: Collection[str],
        namespace: Namespace = None,
        timeout: Optional[float] = None,
        check_period: float = 0.5,
    ):
        """Calling this function will blocks until the pod's status has become {target_status}

        :param target_statuses: return normally when pod's status is one of given statuses
        :param timeout: timeout seconds for this join operation, default to never timeout
        :param check_period: wait interval for polling
        :raises: ReadTargetStatusTimeout
        """
        time_started = time.time()
        pod = None
        while timeout is None or time.time() - time_started < timeout:
            try:
                pod = parse_pod(self.get(name, namespace=namespace))
            except ResourceMissing:
                logger.warning("Pod %s %s not found.", namespace, name)
            else:
                if pod.status.phase in target_statuses:
                    return
            time.sleep(check_period)
        raise ReadTargetStatusTimeout(pod_name=name, max_seconds=timeout, extra_value=pod)

    def get_log(self, name: str, namespace: Namespace, timeout: float = QUERY_LOG_DEFAULT_TIMEOUT, **kwargs):
        # TODO: Use dynamic client instead of `CoreV1Api`
        #
        # This is the only place where we are using the solid type `CoreV1Api`
        # instead of dynamic client in the whole project. The code can be leaved
        # as is because `CoreV1Api` is already a stable API group, but it would
        # be better if we migrate it to code using dynamic client, which is
        # universally across different versions.
        return client_mod.CoreV1Api(self.client).read_namespaced_pod_log(
            name=name, namespace=namespace, _preload_content=False, _request_timeout=timeout, **kwargs
        )


class KDeployment(BaseKresource):
    kind = 'Deployment'


class KStatefulSet(BaseKresource):
    kind = 'StatefulSet'


class KDaemonSet(BaseKresource):
    kind = 'DaemonSet'


class KService(BaseKresource):
    kind = 'Service'


class KIngress(BaseKresource):
    kind = 'Ingress'


class KServiceAccount(BaseKresource):
    kind = 'ServiceAccount'


class KSecret(BaseKresource):
    kind = 'Secret'


class KEvent(BaseKresource):
    kind = "Event"


class KCustomResourceDefinition(BaseKresource):
    kind = "CustomResourceDefinition"


class KConfigMap(BaseKresource):
    kind = 'ConfigMap'


# Individual resource types end


@define
class DeleteOptions:
    """Options for performing deletion"""

    api_version: Optional[Any] = None
    dry_run: Optional[Any] = None
    grace_period_seconds: Optional[Any] = None
    kind: Optional[Any] = None
    orphan_dependents: Optional[Any] = None
    preconditions: Optional[Any] = None
    propagation_policy: Optional[Any] = None
