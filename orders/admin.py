from django.contrib import admin, messages
from django.contrib.admin import action
from django.core.exceptions import ValidationError

from orders.models import Order, OrderItem, OrderStatus
from orders.services import cancel_order


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product', 'quantity', 'price')
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'status', 'payment_method', 'shipping_address',
                    'total_price', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method',)
    search_fields = ('owner__username', 'owner__email')
    inlines = (OrderItemInline,)
    readonly_fields = ('owner', 'created_at', 'updated_at', 'total_price')
    actions = ('cancel_orders',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and 'status' in form.base_fields:
            allowed_statuses = {obj.status}
            allowed_statuses.update(Order.STATUS_TRANSITIONS.get(obj.status, set()))

            if obj.status !=OrderStatus.CANCELLED:
                allowed_statuses.discard(OrderStatus.CANCELLED)

            form.base_fields['status'].choices = [
                (value,label)
                for value, label in OrderStatus.choices
                if value in allowed_statuses
            ]
        return form

    @admin.action(description='Cancel selected orders', permissions=['change'])
    def cancel_orders(self, request, queryset):
        cancelled = 0
        for order in queryset.order_by('pk'):
            try:
                cancelled_order = cancel_order(
                    order_id=order.pk,
                    actor=request.user,
                    allow_admin=True,
                )
            except ValidationError as error:
                self.message_user(
                    request, f'Order #{order.pk}: {" ".join(error.messages)}',
                    level=messages.ERROR,
                )
            else:
                cancelled += 1
                self.log_change(request, cancelled_order, 'Order cancelled; stock restored.')
        if cancelled:
            self.message_user(
                request, f'Cancelled orders: {cancelled}.', level=messages.SUCCESS,
            )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False