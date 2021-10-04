from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path, include, re_path

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/profile/', lambda x: redirect('home')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('bet/', include('betting.urls')),
    path('users/', include('users.urls')),
    re_path('$', lambda x: render(x, 'build/index.html'), name='home'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
