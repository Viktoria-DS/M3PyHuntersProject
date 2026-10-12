from django.urls import path

from orders.apps import OrdersConfig
from orders.views import CartView, CartAddView, CartUpdateView, CartRemoveView, \
    CheckoutView, OrderCancelView, OrderConfirmationView

app_name = OrdersConfig.name

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', CartAddView.as_view(), name='cart_add'),
    path('cart/remove/', CartRemoveView.as_view(), name='cart_remove'),
    # path('cart/clear/', CartClearView.as_view(), name='cart_clear'),
    path('cart/update/', CartUpdateView.as_view(), name='cart_update'),

    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('<int:pk>/cancel/', OrderCancelView.as_view(), name='order_cancel'),
    path('<int:pk>/confirmation/', OrderConfirmationView.as_view(), name='order_confirmation'),
]