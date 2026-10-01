from django.urls import path

from orders.apps import OrdersConfig
from orders.views import CartView, CartAddView, CartUpdateView, CartRemoveView

app_name = OrdersConfig.name

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', CartAddView.as_view(), name='cart_add'),
    path('cart/remove/', CartRemoveView.as_view(), name='cart_remove'),
    # path('cart/clear/', CartClearView.as_view(), name='cart_clear'),
    path('cart/update/', CartUpdateView.as_view(), name='cart_update'),
]