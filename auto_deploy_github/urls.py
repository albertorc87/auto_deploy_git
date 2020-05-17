from django.conf.urls import url
from django.contrib import admin
from django.urls import path
from deploy import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    path(
        route='deploy/', 
        view=views.AutoDeploy,
        name='auto_deploy'
    ),
]
