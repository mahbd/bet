import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles import views
from django.shortcuts import redirect, render
from django.urls import path, include
from django.urls import re_path

from . import admin

admin.site.site_header = 'SuperBetting Admin Panel'
admin.site.index_title = 'Admin Site'

urlpatterns = [
    re_path('accounts/', include('django.contrib.auth.urls')),
    re_path('accounts/profile/', lambda x: redirect('home')),
    re_path('easy-admin/', include('easy_admin.urls')),
    re_path('match-admin/', include('easy_admin.match_url')),
    re_path('admin/', admin.site.urls),
    re_path('api/', include('api.urls')),
    re_path('bet/', include('betting.urls')),
    re_path('users/', include('users.urls')),
    path('__debug__/', include(debug_toolbar.urls)),
    re_path(r'^static/(?P<path>.*)', views.serve),
    re_path('$', lambda x: render(x, 'build/index.html'), name='home'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
