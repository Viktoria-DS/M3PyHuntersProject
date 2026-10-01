from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView

from orders.cart import Cart
from orders.forms import CheckoutForm
from orders.models import OrderItem, Order
from products.models import Product
from django.contrib import messages


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
        context['cart'] = Cart(self.request)
        return context


class CartAddView(TemplateView):
    NEW_PRODUCT = True
    template_name = 'orders/cart.html'

    def post(self, request, *args, **kwargs):
        product_slug = request.POST.get('product_slug')
        product = Product.objects.get(slug=product_slug)
        quantity = int(request.POST.get('quantity', 1))
        cart = Cart(request)
        if self.NEW_PRODUCT:
            messages.success(request, 'Product added to cart')
            cart.add(product, quantity)
        else:
            messages.success(request, 'Product quantity updated')
            cart[product] = quantity
        return redirect_to_cart_source(request)


class CartUpdateView(CartAddView):
    NEW_PRODUCT = False


class CartRemoveView(TemplateView):
    template_name = 'orders/cart.html'

    def post(self, request, *args, **kwargs):
        product_slug = request.POST.get('product_slug')
        product = Product.objects.get(slug=product_slug)
        cart = Cart(request).remove(product)
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
        if form.is_valid():
            # self.update_user(request, form) # update user profile
            self.create_order(request, form)
            return redirect('users:account')
        else:
            messages.error(request, 'Invalid form data')
            return redirect('orders:checkout')

    def create_order(self, request, form):
        cart = Cart(request)
        if not cart.data:
            return redirect('orders:cart')
        order = Order.objects.create(
            owner=request.user,
            payment_method=form.cleaned_data['payment_method'],
            shipping_address=form.cleaned_data['shipping_address'],
        )
        for product_id in cart.data:
            product = Product.objects.get(id=product_id)
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=cart[product],
                price=product.price
            )
        cart.clear()
        messages.success(request, 'Order created successfully')