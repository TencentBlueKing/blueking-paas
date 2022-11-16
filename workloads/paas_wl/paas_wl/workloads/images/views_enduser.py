from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from paas_wl.platform.applications.permissions import AppAction, application_perm_class
from paas_wl.platform.applications.views import ApplicationCodeInPathMixin
from paas_wl.platform.auth.views import BaseEndUserViewSet
from paas_wl.utils.error_codes import error_codes
from paas_wl.workloads.images.models import AppUserCredential
from paas_wl.workloads.images.serializers import UsernamePasswordPairSLZ


class AppUserCredentialViewSet(ApplicationCodeInPathMixin, BaseEndUserViewSet):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(responses={200: UsernamePasswordPairSLZ(many=True)})
    def list(self, request, code):
        """list all username password pair"""
        application = self.get_application()

        instances = AppUserCredential.objects.filter(application_id=application.id).order_by("created")
        return Response(data=UsernamePasswordPairSLZ(instances, many=True).data)

    @swagger_auto_schema(responses={201: UsernamePasswordPairSLZ()}, request_body=UsernamePasswordPairSLZ)
    def create(self, request, code):
        """create a username password pair"""
        application = self.get_application()

        slz = UsernamePasswordPairSLZ(data=request.data)
        slz.is_valid(raise_exception=True)
        try:
            instance = slz.save(application_id=application.id)
        except IntegrityError:
            raise error_codes.CREATE_CREDENTIALS_FAILED.f(_("同名凭证已存在"))
        return Response(data=UsernamePasswordPairSLZ(instance).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(responses={200: UsernamePasswordPairSLZ()}, request_body=UsernamePasswordPairSLZ)
    def update(self, request, code, name):
        """update a username password pair"""
        application = self.get_application()

        instance = get_object_or_404(AppUserCredential, application_id=application.id, name=name)
        slz = UsernamePasswordPairSLZ(data=request.data, instance=instance)
        slz.is_valid(raise_exception=True)
        updated = slz.save()
        return Response(data=UsernamePasswordPairSLZ(updated).data, status=status.HTTP_200_OK)

    def destroy(self, request, code, name):
        """delete a username password pair"""
        application = self.get_application()

        instance = get_object_or_404(AppUserCredential, application_id=application.id, name=name)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
