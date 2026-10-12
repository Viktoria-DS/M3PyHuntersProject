from django.db.models.signals import post_delete
from django.dispatch import receiver

from orders.models import Order, OrderItem


@receiver(post_delete, sender=OrderItem)
def update_order_total_after_item_delete(sender, instance, using, **kwargs):
    order = Order.objects.using(using).filter(pk=instance.order_id).first()
    if order is not None:
        order.update_total_price()