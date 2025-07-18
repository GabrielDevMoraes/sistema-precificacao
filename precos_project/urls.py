# precos_project/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Inclui as URLs do app calculator na raiz do site
    path('', include('calculator.urls')),
    # Inclui as URLs de autenticação (login, logout, etc.)
    path('/contas/login/', include('django.contrib.auth.urls')),
]
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'