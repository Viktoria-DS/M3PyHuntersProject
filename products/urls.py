from products.apps import ProductsConfig
from products.views import ProductListView, GuidesRecipesView
from django.urls import path

app_name = ProductsConfig.name

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('guides-recipes/', GuidesRecipesView.as_view(), name='guides_recipes'),
]