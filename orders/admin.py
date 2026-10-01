from django.contrib import admin, messages
from django.contrib.admin import action
from django.core.exceptions import ValidationError

from orders.models import Order, OrderItem, OrderStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('owner', 'status', 'payment_method', 'shipping_address',
                    'total_price', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method', 'payment_method')
    search_fields = ('owner__username', 'owner__email')
    inlines = (OrderItemInline,)
    readonly_fields = ('created_at', 'updated_at', 'total_price')
    actions = ('cancel_orders',)

    @action(description='Cancel selected orders', permissions=['change'])
    def cancel_orders(self, request, queryset):
        cancelled = 0
        for order in queryset.order_by('pk'):
            try:
                if order.status == OrderStatus.CANCELLED:
                    raise ValidationError('Order is already cancelled.')
                order.status = OrderStatus.CANCELLED
                order.save(update_fields=['status', 'updated_at'])
            except ValidationError as error:
                self.message_user(
                    request, f'Order #{order.pk}: {" ".join(error.messages)}',
                    level=messages.ERROR,
                )
            else:
                cancelled += 1
                self.log_change(request, order, 'Status changed to cancelled.')
        if cancelled:
            self.message_user(
                request, f'Cancelled orders: {cancelled}.', level=messages.SUCCESS,
            )

    def has_delete_permission(self, request, obj=None):
        return False