from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView, DetailView

from orders.cart import Cart
from orders.choices import PAYMENT_METHOD_CHOICES
from orders.forms import CheckoutForm, CartQuantityForm
from orders.models import Order
from orders.services import create_order, cancel_order
from products.models import Product
from django.contrib import messages
from django.db import transaction


def redirect_to_cart_source(request):
    next_url = request.POST.get('next', '').strip()
    if url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
    ):
        return HttpResponseRedirect(next_url)
    return redirect('orders:cart')


class CartView(TemplateView):
    template_name = 'orders/cart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = Cart(self.request).get_summary
        return context


class CartAddView(View):
    NEW_PRODUCT = True
    template_name = 'orders/cart.html'

    def post(self, request, *args, **kwargs):

        form = CartQuantityForm(request.POST)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect('orders:cart')
        product = get_object_or_404(Product, slug=form.cleaned_data['product_slug'])
        quantity = form.cleaned_data['quantity']
        cart = Cart(request)
        try:
            if self.NEW_PRODUCT:
                cart.add(product, quantity)
            else:
                cart[product] = quantity
        except ValidationError as e:
            for message in e.messages:
                messages.error(request, message)
        else:
            messages.success(request, 'Cartupdated successfully')

        return redirect_to_cart_source(request)


class CartUpdateView(CartAddView):
    NEW_PRODUCT = False


class CartRemoveView(View):
    def post(self, request, *args, **kwargs):
        product = get_object_or_404(Product, slug=request.POST.get('product_slug'))
        Cart(request).remove(product)
        messages.success(request, 'Product removed from cart')
        return redirect_to_cart_source(request)

class CheckoutView(LoginRequiredMixin, TemplateView):
    template_name = 'orders/checkout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = Cart(self.request).get_summary
        return context

    def post(self, request, *args, **kwargs):
        form = CheckoutForm(request.POST)

        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect('orders:checkout')

        cart = Cart(request)
        if not cart.data:
            messages.error(request, 'Your cart is empty.')
            return redirect('orders:cart')

        delivery_details = '\n'.join([
            f"Name: {form.cleaned_data['full_name']}",
            f"Phone: {form.cleaned_data['phone']}",
            f"City: {form.cleaned_data['city']}",
            f"Address: {form.cleaned_data['shipping_address']}",
        ])

        try:
            order = create_order(
                owner=request.user,
                items=cart.get_items(),
                shipping_address=delivery_details,
                payment_method=form.cleaned_data['payment_method'],
            )
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return redirect('orders:checkout')

        transaction.on_commit(cart.clear)
        messages.success(
            request,
            f'Order #{order.pk} created successfully',
        )
        return redirect('orders:order_confirmation', pk=order.pk)


class OrderCancelView(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        order = get_object_or_404(
            Order,
            pk=pk,
            owner=request.user,
        )

        try:
            cancel_order(
                order_id=order.pk,
                actor=request.user,
            )
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(
                request,
                f'Order #{order.pk} cancelled successfully.',
            )

        return redirect('users:account')


class OrderConfirmationView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_confirmation.html'
    context_object_name = 'order'
    extra_context = {'title': 'Order confirmation'}

    def get_queryset(self):
        return (
            Order.objects.filter(owner=self.request.user)
            .prefetch_related('items__product')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment_method_label'] = dict(PAYMENT_METHOD_CHOICES).get(self.object.payment_method)
        return context

