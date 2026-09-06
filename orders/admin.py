from django.contrib.admin import action

from orders.models import Order, OrderItem, OrderStatus
from django.contrib import admin
from django.contrib.admin import action

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('owner', 'status', 'payment_method', 'shipping_address', 'total_price', 'created_at', 'updated_at')
    search_fields = ('owner__username', 'owner__email')
    list_filter = ('status', 'payment_method')
    inlines = (OrderItemInline,)
    readonly_fields = ('created_at', 'updated_at', 'total_price')

    @action(description='Cancel selected orders')
    def cancel_orders(self, request, queryset):
        queryset.update(status = OrderStatus.CANCELED)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False


