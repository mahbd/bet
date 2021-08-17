from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles import views
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import re_path

from . import admin
from django.urls import path, include

admin.site.site_header = 'SuperBetting Admin Panel'
admin.site.index_title = 'Admin Site'

urlpatterns = [
    path('', lambda x: HttpResponse(f'Hey {x.user}, This is home'), name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/profile/', lambda x: redirect('home')),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('bet/', include('betting.urls')),
    path('users/', include('users.urls')),
    # path('__debug__/', include(debug_toolbar.urls)),
    re_path(r'^static/(?P<path>.*)$', views.serve)
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
