# -*- coding: utf-8 -*-
from rest_framework import serializers

from paas_wl.networking.egress.models import RCStateAppBinding, RegionClusterState

from .models import format_nodes_data


class RegionClusterStateSLZ(serializers.ModelSerializer):
    class Meta:
        model = RegionClusterState
        # fields = '__all__'
        exclude = ['nodes_digest', 'nodes_data']

    def to_representation(self, obj):
        result = super().to_representation(obj)
        # Format nodes data to IP address only
        nodes_ip_addresses = format_nodes_data(obj.nodes_data)
        result["node_ip_addresses"] = nodes_ip_addresses
        return result


class RCStateAppBindingSLZ(serializers.ModelSerializer):
    state = RegionClusterStateSLZ()

    class Meta:
        model = RCStateAppBinding
        exclude = ['app']
