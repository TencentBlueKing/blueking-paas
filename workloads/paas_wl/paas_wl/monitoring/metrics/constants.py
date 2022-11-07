# -*- coding: utf-8 -*-
from blue_krill.data_types.enum import EnumField, StructuredEnum


class MetricsSeriesType(str, StructuredEnum):
    CURRENT = EnumField('current', '使用量')
    REQUEST = EnumField('request', '保留量')
    LIMIT = EnumField('limit', '配额上限')


class MetricsResourceType(str, StructuredEnum):
    MEM = EnumField('mem')
    CPU = EnumField('cpu')
    NETWORK_IO = EnumField('network_io')

    @classmethod
    def choices(cls):
        """Return original choice tuples with an extra value: __all__"""
        choices = super().get_django_choices()
        return choices + [('__all__', '__ALL__')]


PROMQL_TMPL = {
    "mem": {
        "current": 'sum by(container_name) '
        '(container_memory_working_set_bytes{{'
        'pod_name="{instance_name}", container_name!="POD", cluster_id="{cluster_id}"}})',
        "request": 'kube_pod_container_resource_requests_memory_bytes{{'
        'pod="{instance_name}", cluster_id="{cluster_id}"}}',
        "limit": 'kube_pod_container_resource_limits_memory_bytes{{'
        'pod="{instance_name}", cluster_id="{cluster_id}"}}',
    },
    "cpu": {
        "current": 'sum by (container_name)'
        '(rate(container_cpu_usage_seconds_total{{'
        'image!="",container_name!="POD",pod_name="{instance_name}", cluster_id="{cluster_id}"}}[1m]))',
        "request": 'kube_pod_container_resource_requests_cpu_cores{{pod="{instance_name}", cluster_id="{cluster_id}"}}',  # noqa
        "limit": 'kube_pod_container_resource_limits_cpu_cores{{pod="{instance_name}", cluster_id="{cluster_id}"}}',
    },
}
