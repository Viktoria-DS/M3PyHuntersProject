from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView

from orders.cart import Cart
from products.models import Product


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
            cart.add(product, quantity)
        else:
            cart.set_quantity(product, quantity)
        return redirect_to_cart_source(request)


class CartUpdateView(CartAddView):
    NEW_PRODUCT = False


class CartRemoveView(TemplateView):
    template_name = 'orders/cart.html'

    def post(self, request, *args, **kwargs):
        product_slug = request.POST.get('product_slug')
        product = Product.objects.get(slug=product_slug)
        cart = Cart(request).remove(product)
        return redirect_to_cart_source(request)