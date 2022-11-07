# -*- coding: utf-8 -*-
from blue_krill.data_types.enum import EnumField, StructuredEnum


class AppAddOnType(int, StructuredEnum):
    SIMPLE_SIDECAR = EnumField(1, label="SideCar Container")
    READINESS_PROBE = EnumField(2, label="Readiness Probe")
    VOLUME_MOUNT = EnumField(3, label="Volume Mount Point")
    VOLUME = EnumField(4, label="Volume to Mount")
