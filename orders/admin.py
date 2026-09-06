from orders.models import Order, OrderItem
from django.contrib import admin


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('owner', 'status', 'payment_method', 'shipping_address' 'total_price', 'created_at', 'updated_at')
    search_fields = ('owner__username', 'owner__email')
    list_filter = ('status', 'payment_method')
    inlines = (OrderItemInline,)
    readonly_fields = ('created_at', 'updated_at')


