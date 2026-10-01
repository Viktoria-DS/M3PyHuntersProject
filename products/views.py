import logging

from django.db.models import Q, QuerySet
from django.db.models.aggregates import Avg
from django.shortcuts import render
from django.views.generic import ListView, TemplateView, DetailView

from products.models import Product, Category


# Create your views here.
class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 5
    ordering = ['-created_at']

    queryset = (Product.objects.all()
                .select_related('category')
                .prefetch_related('reviews')
                .annotate(rating=Avg('reviews__rating')))
    ORDERING_FIELDS = ['price', '-price', 'created_at', '-created_at',
                       'name', '-name', 'rating', '-rating'
                       ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

    def get_queryset(self) -> QuerySet:
        q = super().get_queryset()
        cats = self.request.GET.get('categories')
        sorting = self.request.GET.get('sorting')
        search = self.request.GET.get('search')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        logging.debug(f'Get params: {self.request.GET}')
        if cats:
            cats = cats.split(',')
            q = q.filter(category__slug__in=cats)
        if search:
            q = q.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        if min_price:
            try:
                q = q.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass
        if max_price:
            try:
                q = q.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass
        if sorting and sorting in self.ORDERING_FIELDS:
            q = q.order_by(sorting)
        return q

class GuidesRecipesView(TemplateView):
    template_name = 'products/guides_recipes.html'

class ProductDetailView(DetailView):
    template_name = 'products/product_detail.html'
    queryset = (Product.objects.all()
                .select_related('category')
                .prefetch_related('reviews'))


    def get_context_data(self, **kwargs):
        product = Product.objects.get(slug=self.kwargs['slug'])
        context = super().get_context_data(**kwargs)
        context['product'] = product
        return context