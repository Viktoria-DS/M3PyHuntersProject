from django.shortcuts import render
from django.views.generic import ListView, TemplateView, DetailView

from products.models import Product


# Create your views here.
class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'

class GuidesRecipesView(TemplateView):
    template_name = 'products/guides_recipes.html'

class ProductDetailView(DetailView):
    template_name = 'products/product_detail.html'
    queryset = Product.objects.all().select_related('category').prefetch_related('reviews')
    def get_context_data(self, **kwargs):
        product = Product.objects.get(slug=self.kwargs['slug'])
        context = super().get_context_data(**kwargs)
        context['product'] = product
        return context