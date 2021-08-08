from django.contrib import admin
from django.urls import path, include

admin.site.site_header = 'SuperBetting Admin Panel'
admin.site.index_title = 'Admin Site'

urlpatterns = [
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('bet/', include('betting.urls')),
    path('users/', include('users.urls'))
]
