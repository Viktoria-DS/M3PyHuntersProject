from django.http import HttpRequest

from products.models import Product


class Cart:
    CART_SESSION_KEY = 'cart'
    CART_SESSION_VERSION_KEY = 'cart_version'
    CART_SESSION_VERSION = 2

    def __init__(self, request: HttpRequest):
        self.session = request.session
        self.session.setdefault(Cart.CART_SESSION_KEY, {})
        self.data: dict[str, int] = self.session[Cart.CART_SESSION_KEY]
        if self.session.get(self.CART_SESSION_VERSION_KEY) != self.CART_SESSION_VERSION:
            self.migrate_slug_keys()

    def migrate_slug_keys(self):
        products_by_slug = Product.objects.in_bulk(self.data, field_name='slug')
        migrated_data = {}
        for slug, quantity in self.data.items():
            product = products_by_slug.get(slug)
            if product is not None:
                product_id = str(product.pk)
                migrated_data[product_id] = migrated_data.get(product_id, 0) + quantity
        self.data = migrated_data
        self.session[self.CART_SESSION_VERSION_KEY] = self.CART_SESSION_VERSION
        self.save()

    def save(self):
        self.session[Cart.CART_SESSION_KEY] = self.data
        self.session.modified = True

    def __setitem__(self, product: Product, quantity: int):
        self.data[str(product.pk)] = quantity
        self.save()

    def add(self, product: Product, quantity: int):
        self[product] = quantity + self[product]
        self.save()

    def remove(self, product: Product):
        self.data.pop(str(product.pk), None)
        self.save()

    def clear(self):
        self.data.clear()
        self.save()

    def get_items(self):
        return [
            {
                'product_id': p,
                'quantity': q
            }
            for p, q in self.data.items()
        ]

    def __getitem__(self, product: Product):
        return self.data.get(str(product.pk), 0)

    @property
    def get_summary(self):
        total = 0
        products = []
        products_by_id = Product.objects.in_bulk(self.data)
        missing_product_ids = []
        for product_id, quantity in self.data.items():
            product = products_by_id.get(int(product_id))
            if product is None:
                missing_product_ids.append(product_id)
                continue
            position_product_price = product.price * quantity
            total += position_product_price
            products.append(
                {
                    'product': product,
                    'quantity': quantity,
                    'position_price': position_product_price
                }
            )
        for product_id in missing_product_ids:
            self.data.pop(product_id)
        if missing_product_ids:
            self.save()
        return {
            'total': total,
            'products': products
        }