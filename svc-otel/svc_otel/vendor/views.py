# -*- coding: utf-8 -*-
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthzView(APIView):
    def get(self, request):
        return Response(
            {
                "result": True,
                "data": {},
                "message": "",
            }
        )
