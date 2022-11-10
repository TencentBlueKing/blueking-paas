from rest_framework import status
from rest_framework.response import Response

from paas_wl.platform.system_api.views import SysViewSet

from .models import AppModelResource, create_app_resource
from .serializers import AppModelResourceSerializer, CreateAppModelResourceSerializer


class AppModelResourceViewSet(SysViewSet):
    def create(self, request, region: str):
        """Create the AppModelResource object for Module"""
        serializer = CreateAppModelResourceSerializer(data=request.data)
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
        return Response(AppModelResourceSerializer(model_resource).data, status=status.HTTP_201_CREATED)
