from django.urls import path

from products.views import ProductList, GuidesRecipesView, ProductDetailsView

from products.apps import ProductsConfig

app_name = ProductsConfig.name

urlpatterns = [
    path('', ProductList.as_view(), name='product_list'),
    path('guides-recipes/', GuidesRecipesView.as_view(), name='guides_recipes'),
    path('<slug:slug>/', ProductDetailsView.as_view(), name='product_details'),

]