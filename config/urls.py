from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.auth_urls')),
    path('api/', include('apps.accounts.urls')), 
    path('api/', include('apps.reforestation.urls')), 
    path('api/', include('apps.finances.urls')),
    path('api/', include('apps.audit.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),

    # Documentation OpenAPI — à montrer en soutenance
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]