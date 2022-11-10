# -*- coding: utf-8 -*-
"""Utilities for auto generate swagger API documents
"""
from drf_yasg import openapi

openapi_empty_schema = openapi.Schema(type='object')
openapi_empty_response = openapi.Response('操作成功后的空响应', schema=openapi_empty_schema)
