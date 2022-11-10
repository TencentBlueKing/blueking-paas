from django.urls import re_path

from paas_wl.utils import text

from . import views

urlpatterns = [
    re_path(
        f'^regions/{text.PVAR_REGION}/app_model_resources/$', views.AppModelResourceViewSet.as_view({'post': 'create'})
    ),
]
