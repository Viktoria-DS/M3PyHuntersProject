from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from api.views import ProductViewSet, OrderViewSet, PasswordResetRequestView, PasswordResetConfirmView, \
    PasswordChangeAPIView
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView
router = DefaultRouter()
router.register('products', ProductViewSet, basename='api-product')
router.register('orders', OrderViewSet, basename='api-order')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('', include(router.urls)),
    path('reset_password/', PasswordResetRequestView.as_view(), name='api_reset_password'),
    path('reset_password_confirm/', PasswordResetConfirmView.as_view(), name='api_reset_password_confirm'),
    path('change_password/', PasswordChangeAPIView.as_view(), name='api_password_change'),
]