import logging
from django.db.models import Q, QuerySet, Avg, OuterRef, Sum, Subquery
from django.db.models.functions import Coalesce
from django.views.generic import ListView, TemplateView, DetailView

from orders.cart import Cart
from orders.models import OrderItem, OrderStatus
from products.forms import ProductPriceFilterForm
from products.models import Product, Category
from reviews.forms import ReviewForm


class ProductList(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 6
    ordering = ['-created_at']
    sales = (OrderItem.objects.filter(
        product_id = OuterRef('pk'),
        order__status__in = [
            OrderStatus.PAID,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED
        ]
    )
    .order_by()
    .values('product_id')
    .annotate(total = Sum('quantity'))
    .values('total')
)

    queryset = (Product.objects.filter(is_active=True).select_related('category').prefetch_related('reviews').
                annotate(rating = Avg('reviews__rating'), popularity = Coalesce(Subquery(sales), 0)))

    ORDERING_FIELDS = ['price', '-price', 'created_at', '-created_at',
                       'name', '-name', 'rating', '-rating', 'popularity', '-popularity'
                       ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['price_form'] = self.price_form
        return context

    def get_queryset(self) -> QuerySet:
        q = super().get_queryset()
        self.price_form = ProductPriceFilterForm(self.request.GET)
        cats = self.request.GET.get('categories')
        sorting = self.request.GET.get('sorting')
        search = self.request.GET.get('search')

        if cats:
            cats = cats.split(',')
            q = q.filter(category__slug__in=cats)
        if search:
            q = q.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        if self.price_form.is_valid():
            minimum = self.price_form.cleaned_data['min_price']
            maximum = self.price_form.cleaned_data['max_price']

            if minimum is not None:
                q = q.filter(price__gte=minimum)

            if maximum is not None:
                q = q.filter(price__lte=maximum)
        if sorting and sorting in self.ORDERING_FIELDS:
            q = q.order_by(sorting, 'pk')
        return q


class GuidesRecipesView(TemplateView):
    template_name = 'products/guides_recipes.html'


class ProductDetailsView(DetailView):
    template_name = 'products/product_detail.html'
    queryset = (Product.objects.all()
                .select_related('category')
                .prefetch_related('reviews__owner')
                .annotate(average_rating = Avg('reviews__rating')))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = Cart(self.request)
        context['cart'] = cart.get_summary
        context['product_in_cart'] = cart[self.object]
        context['review_form'] = ReviewForm()
        context['has_reviewed'] = False
        context['has_delivered_order'] = False

        if self.request.user.is_authenticated:
            context['has_reviewed'] = (self.object.reviews.filter(owner=self.request.user).exists())

            context['has_delivered_order'] = OrderItem.objects.filter(
                    order__owner=self.request.user,
                    order__status=OrderStatus.DELIVERED,
                    product = self.object
                ).exists()

        context['can_review'] = (not context['has_reviewed'] and context['has_delivered_order'])

        return context