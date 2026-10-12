from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F

from orders.choices import PAYMENT_METHOD_CHOICES
from orders.models import Order, OrderItem, OrderStatus
from products.models import Product


@transaction.atomic
def create_order(*, owner, items, shipping_address, payment_method):
    if not getattr(owner, 'is_authenticated', False):
        raise PermissionDenied('Log in to create an order.')
    if not isinstance(items, (list, tuple)) or not items:
        raise ValidationError('Order items must be a nonempty list.')
    if not isinstance(shipping_address, str) or not shipping_address.strip():
        raise ValidationError('Shipping address is required.')
    if (
        not isinstance(payment_method, str)
        or payment_method not in dict(PAYMENT_METHOD_CHOICES)
    ):
        raise ValidationError('Choose a valid payment method.')

    quantities = defaultdict(int)
    for item in items:
        if (
            not isinstance(item, dict)
            or set(item) != {'product_id', 'quantity'}
        ):
            raise ValidationError(
                'Each order item must contain only product_id and quantity.'
            )

        product_id = item['product_id']
        if (
            isinstance(product_id, bool)
            or not isinstance(product_id, (int, str))
        ):
            raise ValidationError('Product ID must be a positive whole number.')
        try:
            product_id = int(product_id)
        except ValueError:
            raise ValidationError(
                'Product ID must be a positive whole number.'
            ) from None
        if product_id < 1:
            raise ValidationError('Product ID must be a positive whole number.')

        quantity = item['quantity']
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 1
        ):
            raise ValidationError('Quantity must be a positive whole number.')
        quantities[product_id] += quantity

    # Lock products in a stable order before checking or changing stock.
    products = list(
        Product.objects.select_for_update()
        .filter(pk__in=quantities)
        .order_by('pk')
    )
    if len(products) != len(quantities):
        raise ValidationError('A product in your cart no longer exists.')

    total = Decimal('0.00')
    for product in products:
        quantity = quantities[product.pk]
        if not product.is_active:
            raise ValidationError(f'{product.name} is no longer available.')
        if quantity > product.stock:
            raise ValidationError(
                f'Not enough {product.name} in stock. '
                f'Available: {product.stock}.'
            )
        total += product.price * quantity

    order = Order(
        owner=owner,
        status=OrderStatus.PENDING,
        shipping_address=shipping_address.strip(),
        payment_method=payment_method,
        total_price=total,
    )
    order.full_clean()
    order.save()

    for product in products:
        quantity = quantities[product.pk]
        order_item = OrderItem(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price,
        )
        order_item.full_clean()
        order_item.save()

        updated = Product.objects.filter(
            pk=product.pk,
            stock__gte=quantity,
        ).update(stock=F('stock') - quantity)
        if updated != 1:
            raise ValidationError(f'Not enough {product.name} in stock.')

    return order


@transaction.atomic
def cancel_order(*, order_id, actor, allow_admin = False):
    if not actor.is_authenticated:
        raise PermissionDenied('Log in to cancel an order.')
    order = Order.objects.select_for_update().get(pk=order_id)
    is_admin = allow_admin and (actor.is_staff or actor.is_superuser)
    if not is_admin and order.owner_id != actor.pk:
        raise PermissionDenied('You may only cancel your own orders.')
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError('Order is already cancelled.')
    if not is_admin and order.status != OrderStatus.PENDING:
        raise ValidationError('You may only cancel a pending order.')
    if OrderStatus.CANCELLED not in Order.STATUS_TRANSITIONS.get(
        order.status, set()
    ):
        raise ValidationError('This order cannot be cancelled.')

    items = list(order.items.order_by('product_id'))

    products = list(
        Product.objects.select_for_update()
        .filter(pk__in=[item.product_id for item in items])
        .order_by('pk')
    )
    if len(products) != len({item.product_id for item in items}):
        raise ValidationError('An order product could not be restored.')

    for item in items:
        Product.objects.filter(pk = item.product_id).update(
            stock=F('stock') + item.quantity
        )

    order.status = OrderStatus.CANCELLED
    order.save(update_fields = ['status', 'updated_at'])

    return order