from django.shortcuts import render
from django.views.generic import ListView, TemplateView

from products.models import Product


# Create your views here.
class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'

class GuidesRecipesView(TemplateView):
    template_name = 'products/guides_recipes.html'