from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView

from orders.models import OrderItem, OrderStatus
from products.models import Product
from reviews.forms import ReviewForm
from reviews.models import Review


class ReviewCreateView(LoginRequiredMixin, CreateView):
    model = Review
    form_class = ReviewForm
    http_method_names = ['post', 'options']

    def form_valid(self, form):
        product = get_object_or_404(Product, slug = self.kwargs['slug'])

        has_delivered_order = OrderItem.objects.filter(
            order__owner = self.request.user,
            order__status = OrderStatus.DELIVERED,
            product = product,
        ).exists()

        if not has_delivered_order:
            form.add_error(None, "You can review the product after delivery")
            return self.form_invalid(form)

        existing_reviews = Review.objects.filter(owner = self.request.user, product = product)

        if existing_reviews.exists():
            form.add_error(None, "You have already reviewed this product")
            return self.form_invalid(form)

        form.instance.owner = self.request.user
        form.instance.product = product

        try:
            with transaction.atomic():
                response = super().form_valid(form)

        except IntegrityError:
            if not existing_reviews.exists():
                raise
            form.add_error(None, "You have already reviewed this product")
            return self.form_invalid(form)

        messages.success(self.request, "Your review was successfully published")

        return response

    def form_invalid(self, form):
        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return  redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            'products:product_details',
            kwargs={'slug': self.kwargs['slug']},
        )






