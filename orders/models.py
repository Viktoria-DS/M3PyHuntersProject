from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum


class OrderStatus(models.TextChoices):
    PENDING = 'pending'
    PAID = 'paid'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'


class Order(models.Model):
    STATUS_TRANSITIONS = {
        OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
        OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
        OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
        OrderStatus.DELIVERED: set(),
        OrderStatus.CANCELLED: set(),
    }

    owner = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=OrderStatus.choices,
                              default=OrderStatus.PENDING)
    payment_method = models.CharField(max_length=100)
    shipping_address = models.CharField(max_length=255)
    total_price = models.DecimalField(default=0, max_digits=10,
                                      decimal_places=2,
                                      validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.owner} - {self.status}"

    def get_absolute_url(self):
        return f'/orders/{self.id}'

    def validate_status_transition(self):
        if self.status not in OrderStatus.values:
            raise ValidationError({'status': 'Unknown order status.'})
        if self._state.adding:
            if self.status != OrderStatus.PENDING:
                raise ValidationError({
                    'status': 'New orders must have pending status.',
                })
            return

        current_status = (Order.objects.values_list('status', flat=True)
                          .get(pk=self.pk))
        if self.status == current_status:
            return
        if self.status not in self.STATUS_TRANSITIONS.get(current_status, set()):
            raise ValidationError({
                'status': f'Cannot change status from {current_status} to {self.status}.',
            })

    def clean(self):
        super().clean()
        self.validate_status_transition()

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'status' in update_fields:
            self.validate_status_transition()
        super().save(*args, **kwargs)

    def update_total_price(self):
        stats = self.items.aggregate(
            total=Sum(F('price') * F('quantity')))

        self.total_price = stats['total'] or 0
        self.save(update_fields=['total_price'])

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.order.update_total_price()

    def __str__(self):
        return f"{self.product} - {self.quantity}"

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"