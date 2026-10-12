import re
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import ERROR, SUCCESS, get_messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from orders.models import Order, OrderStatus
from orders.services import cancel_order, create_order
from products.models import Category, Product
from reviews.models import Review


pytestmark = pytest.mark.django_db

PASSWORD = 'StrongTestPassword42!'


# Reusable test data

@pytest.fixture
def buyer():
    return get_user_model().objects.create_user(
        username='buyer',
        password=PASSWORD,
    )


@pytest.fixture
def other_user():
    return get_user_model().objects.create_user(
        username='other',
        password=PASSWORD,
    )


@pytest.fixture
def product():
    category = Category.objects.create(name='Ingredients')

    return Product.objects.create(
        name='Test product',
        description='Roasted ingredients',
        category=category,
        price=Decimal('10.00'),
        stock=10,
        image='products/test.jpg',
    )


@pytest.fixture
def make_order(buyer, product):
    def factory(
        owner=None,
        item=None,
        quantity=2,
        status=OrderStatus.PENDING,
    ):
        order = create_order(
            owner=owner or buyer,
            items=[{
                'product_id': (item or product).pk,
                'quantity': quantity,
            }],
            shipping_address='Test street 1',
            payment_method='cod',
        )

        for next_status in (
            OrderStatus.PAID,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ):
            if order.status == status:
                break

            order.status = next_status
            order.save(update_fields=['status'])

        return order

    return factory


@pytest.fixture
def api_client(buyer):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(buyer)}',
    )
    return client


@pytest.fixture
def order_data(product):
    return {
        'items': [{'product_id': product.pk, 'quantity': 2}],
        'shipping_address': 'Test street 1',
        'payment_method': 'cod',
    }


def add_to_cart(client, product, quantity=2):
    return client.post(
        reverse('orders:cart_add'),
        {
            'product_slug': product.slug,
            'quantity': quantity,
        },
    )


def checkout_data():
    return {
        'full_name': 'Test Buyer',
        'phone': '+79991234567',
        'city': 'Test City',
        'shipping_address': 'Test street 1',
        'payment_method': 'cod',
    }


from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from orders.models import Order, OrderItem, OrderStatus
from orders.services import create_order
from products.models import Category, Product


class CreateOrderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='buyer')
        category = Category.objects.create(name='Test category')
        cls.first = Product.objects.create(
            name='First product',
            category=category,
            price=Decimal('10.00'),
            stock=10,
            image='products/test.jpg',
        )
        cls.second = Product.objects.create(
            name='Second product',
            category=category,
            price=Decimal('3.50'),
            stock=8,
            image='products/test.jpg',
        )

    def place_order(self, **overrides):
        arguments = {
            'owner': self.owner,
            'items': [{'product_id': str(self.first.pk), 'quantity': 2}],
            'shipping_address': '  Test street 1  ',
            'payment_method': 'cod',
        }
        arguments.update(overrides)
        return create_order(**arguments)

    def assert_nothing_created(self):
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(Product.objects.get(pk=self.first.pk).stock, 10)
        self.assertEqual(Product.objects.get(pk=self.second.pk).stock, 8)

    def test_multiple_products_create_one_complete_order(self):
        order = self.place_order(items=[
            {'product_id': str(self.first.pk), 'quantity': 2},
            {'product_id': self.second.pk, 'quantity': 3},
        ])
        order.refresh_from_db()
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(order.owner, self.owner)
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.shipping_address, 'Test street 1')
        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual(order.total_price, Decimal('30.50'))
        self.assertEqual(
            set(order.items.values_list('product_id', 'quantity', 'price')),
            {
                (self.first.pk, 2, Decimal('10.00')),
                (self.second.pk, 3, Decimal('3.50')),
            },
        )
        self.assertEqual(Product.objects.get(pk=self.first.pk).stock, 8)
        self.assertEqual(Product.objects.get(pk=self.second.pk).stock, 5)

    def test_duplicate_product_entries_are_merged(self):
        order = self.place_order(items=[
            {'product_id': str(self.first.pk), 'quantity': 2},
            {'product_id': self.first.pk, 'quantity': 3},
        ])
        item = order.items.get()
        self.assertEqual(item.quantity, 5)
        self.assertEqual(order.total_price, Decimal('50.00'))
        self.assertEqual(Product.objects.get(pk=self.first.pk).stock, 5)

    def test_combined_duplicate_quantity_must_fit_stock(self):
        with self.assertRaises(ValidationError):
            self.place_order(items=[
                {'product_id': self.first.pk, 'quantity': 6},
                {'product_id': self.first.pk, 'quantity': 5},
            ])
        self.assert_nothing_created()

    def test_prices_remain_snapshots_after_product_price_changes(self):
        order = self.place_order()
        Product.objects.filter(pk=self.first.pk).update(price=Decimal('99.00'))
        order.refresh_from_db()
        self.assertEqual(order.items.get().price, Decimal('10.00'))
        self.assertEqual(order.total_price, Decimal('20.00'))

    def test_order_creation_requires_authentication(self):
        with self.assertRaises(PermissionDenied):
            self.place_order(owner=AnonymousUser())
        self.assert_nothing_created()

    def test_empty_or_invalid_item_lists_are_rejected(self):
        for items in ([], (), None, {}, 'not a list'):
            with self.subTest(items=items):
                with self.assertRaises(ValidationError):
                    self.place_order(items=items)
                self.assert_nothing_created()

    def test_malformed_entries_and_client_prices_are_rejected(self):
        for item in (
            None,
            [],
            {},
            {'product_id': self.first.pk},
            {'quantity': 1},
            {'product_id': self.first.pk, 'quantity': 1, 'price': '0.01'},
        ):
            with self.subTest(item=item):
                with self.assertRaises(ValidationError):
                    self.place_order(items=[item])
                self.assert_nothing_created()

    def test_invalid_product_ids_are_rejected(self):
        for product_id in (0, -1, True, 1.5, 'invalid', None):
            with self.subTest(product_id=product_id):
                with self.assertRaises(ValidationError):
                    self.place_order(items=[
                        {'product_id': product_id, 'quantity': 1},
                    ])
                self.assert_nothing_created()

    def test_quantities_must_be_positive_integers(self):
        for quantity in (0, -1, True, 1.5, '2', None):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValidationError):
                    self.place_order(items=[
                        {'product_id': self.first.pk, 'quantity': quantity},
                    ])
                self.assert_nothing_created()

    def test_invalid_second_item_does_not_create_a_partial_order(self):
        with self.assertRaises(ValidationError):
            self.place_order(items=[
                {'product_id': self.first.pk, 'quantity': 2},
                {'product_id': self.second.pk, 'quantity': 0},
            ])
        self.assert_nothing_created()

    def test_missing_second_product_does_not_create_a_partial_order(self):
        with self.assertRaises(ValidationError):
            self.place_order(items=[
                {'product_id': self.first.pk, 'quantity': 2},
                {'product_id': self.second.pk + 10000, 'quantity': 1},
            ])
        self.assert_nothing_created()

    def test_inactive_second_product_does_not_create_a_partial_order(self):
        Product.objects.filter(pk=self.second.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.place_order(items=[
                {'product_id': self.first.pk, 'quantity': 2},
                {'product_id': self.second.pk, 'quantity': 1},
            ])
        self.assert_nothing_created()

    def test_insufficient_second_product_stock_rejects_the_whole_order(self):
        with self.assertRaises(ValidationError):
            self.place_order(items=[
                {'product_id': self.first.pk, 'quantity': 2},
                {'product_id': self.second.pk, 'quantity': 9},
            ])
        self.assert_nothing_created()

    def test_shipping_address_is_required(self):
        for address in ('', '   ', None, 123):
            with self.subTest(address=address):
                with self.assertRaises(ValidationError):
                    self.place_order(shipping_address=address)
                self.assert_nothing_created()
    def test_unsupported_payment_methods_are_rejected(self):
        for payment_method in ('', 'unknown', None, []):
            with self.subTest(payment_method=payment_method):
                with self.assertRaises(ValidationError):
                    self.place_order(payment_method=payment_method)
                self.assert_nothing_created()

    def test_each_checkout_payment_method_is_supported(self):
        for method in ('debit', 'wallet', 'cod'):
            with self.subTest(method=method):
                order = self.place_order(
                    items=[{'product_id': self.first.pk, 'quantity': 1}],
                    payment_method=method,
                )
                self.assertEqual(order.payment_method, method)
                self.assertEqual(order.status, OrderStatus.PENDING)

    def test_late_failure_rolls_back_items_order_and_stock(self):
        original_save = OrderItem.save
        saved_items = 0

        def fail_on_second_item(instance, *args, **kwargs):
            nonlocal saved_items
            saved_items += 1
            if saved_items == 2:
                raise RuntimeError('Simulated order-item save failure.')
            return original_save(instance, *args, **kwargs)

        with patch.object(OrderItem, 'save', autospec=True,
                          side_effect=fail_on_second_item):
            with self.assertRaises(RuntimeError):
                self.place_order(items=[
                    {'product_id': self.first.pk, 'quantity': 2},
                    {'product_id': self.second.pk, 'quantity': 3},
                ])
        self.assertEqual(saved_items, 2)
        self.assert_nothing_created()



# Order rules

def test_cancellation_checks_owner_and_restores_stock_once(
    buyer, other_user, product, make_order,
):
    order = make_order()

    with pytest.raises(PermissionDenied):
        cancel_order(order_id=order.pk, actor=other_user)

    order.refresh_from_db()
    product.refresh_from_db()
    assert order.status == OrderStatus.PENDING
    assert product.stock == 8

    cancelled = cancel_order(order_id=order.pk, actor=buyer)

    product.refresh_from_db()
    assert cancelled.status == OrderStatus.CANCELLED
    assert product.stock == 10
    assert Order.objects.filter(pk=order.pk).exists()

    with pytest.raises(ValidationError):
        cancel_order(order_id=order.pk, actor=buyer)

    product.refresh_from_db()
    assert product.stock == 10


@pytest.mark.parametrize('status', [
    OrderStatus.PAID,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
])
def test_customer_cannot_cancel_nonpending_order(
    buyer, product, make_order, status,
):
    order = make_order(status=status)

    with pytest.raises(ValidationError):
        cancel_order(order_id=order.pk, actor=buyer)

    order.refresh_from_db()
    product.refresh_from_db()
    assert order.status == status
    assert product.stock == 8

    if status == OrderStatus.PAID:
        buyer.is_staff = True
        buyer.save(update_fields=['is_staff'])

        cancelled = cancel_order(
            order_id=order.pk,
            actor=buyer,
            allow_admin=True,
        )

        product.refresh_from_db()
        assert cancelled.status == OrderStatus.CANCELLED
        assert product.stock == 10


def test_statuses_follow_allowed_transitions(make_order):
    order = make_order()
    order.status = OrderStatus.DELIVERED

    with pytest.raises(ValidationError):
        order.save(update_fields=['status'])

    order.refresh_from_db()
    assert order.status == OrderStatus.PENDING

    for status in (
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ):
        order.status = status
        order.save(update_fields=['status'])

        order.refresh_from_db()
        assert order.status == status

    order.status = OrderStatus.PAID

    with pytest.raises(ValidationError):
        order.save(update_fields=['status'])


def test_admin_cannot_delete_order(client, buyer, make_order):
    buyer.is_staff = True
    buyer.is_superuser = True
    buyer.save(update_fields=['is_staff', 'is_superuser'])
    client.force_login(buyer)

    order = make_order()
    response = client.post(
        reverse('admin:orders_order_delete', args=[order.pk]),
        {'post': 'yes'},
    )

    assert response.status_code == 403
    assert Order.objects.filter(pk=order.pk).exists()


# Cart and checkout

def test_cart_add_update_remove_and_availability(client, product):
    add_to_cart(client, product)
    add_to_cart(client, product, quantity=1)

    assert client.session['cart'] == {str(product.pk): 3}

    response = client.get(reverse('orders:cart'))
    assert response.status_code == 200
    assert response.context['cart']['total'] == Decimal('30.00')

    response = add_to_cart(client, product, quantity=8)
    assert client.session['cart'] == {str(product.pk): 3}
    assert any(
        m.level == ERROR for m in get_messages(response.wsgi_request)
    )

    product.is_active = False
    product.save(update_fields=['is_active'])
    add_to_cart(client, product, quantity=1)

    assert client.session['cart'] == {str(product.pk): 3}

    product.is_active = True
    product.save(update_fields=['is_active'])

    client.post(reverse('orders:cart_update'), {
        'product_slug': product.slug,
        'quantity': 1,
    })
    assert client.session['cart'] == {str(product.pk): 1}

    client.post(reverse('orders:cart_update'), {
        'product_slug': product.slug,
        'quantity': 0,
    })
    assert client.session['cart'] == {}

    add_to_cart(client, product)
    client.post(reverse('orders:cart_remove'), {
        'product_slug': product.slug,
    })
    assert client.session['cart'] == {}


@pytest.mark.django_db(transaction=True)
def test_checkout_saves_delivery_data_and_clears_cart(
    client, buyer, product,
):
    client.force_login(buyer)
    add_to_cart(client, product)

    response = client.post(
        reverse('orders:checkout'),
        checkout_data(),
    )

    order = Order.objects.get()

    assert response.status_code == 302
    assert response.url == reverse(
        'orders:order_confirmation',
        args=[order.pk],
    )
    assert order.owner == buyer
    assert order.status == OrderStatus.PENDING
    assert order.payment_method == 'cod'
    assert order.total_price == Decimal('20.00')
    assert order.shipping_address == (
        'Name: Test Buyer\n'
        'Phone: +79991234567\n'
        'City: Test City\n'
        'Address: Test street 1'
    )
    assert client.session['cart'] == {}

    product.refresh_from_db()
    assert product.stock == 8
    assert any(
        m.level == SUCCESS for m in get_messages(response.wsgi_request)
    )
    assert client.get(response.url).status_code == 200


def test_failed_checkout_preserves_cart(client, buyer, product):
    client.force_login(buyer)
    add_to_cart(client, product)

    data = checkout_data()
    data['full_name'] = ''

    response = client.post(reverse('orders:checkout'), data)

    assert response.status_code == 302
    assert not Order.objects.exists()
    assert client.session['cart'] == {str(product.pk): 2}

    product.stock = 1
    product.save(update_fields=['stock'])

    response = client.post(
        reverse('orders:checkout'),
        checkout_data(),
    )

    assert response.status_code == 302
    assert not Order.objects.exists()
    assert client.session['cart'] == {str(product.pk): 2}

    product.refresh_from_db()
    assert product.stock == 1
    assert any(
        m.level == ERROR for m in get_messages(response.wsgi_request)
    )


# Accounts

def test_registration_login_logout_and_cart_preservation(client, product):
    for name in ('users:account', 'orders:checkout'):
        response = client.get(reverse(name))

        assert response.status_code == 302
        assert reverse('users:login') in response.url

    add_to_cart(client, product)

    response = client.post(reverse('users:register'), {
        'username': 'newbuyer',
        'email': 'buyer@example.com',
        'first_name': 'Test',
        'last_name': 'Buyer',
        'password1': PASSWORD,
        'password2': PASSWORD,
    })

    assert response.status_code == 302

    user = get_user_model().objects.get(username='newbuyer')
    assert user.check_password(PASSWORD)

    response = client.post(reverse('users:login'), {
        'username': 'newbuyer',
        'password': PASSWORD,
        'next': reverse('users:account'),
    })

    assert response.status_code == 302
    assert client.session['_auth_user_id'] == str(user.pk)
    assert client.session['cart'] == {str(product.pk): 2}

    response = client.post(reverse('users:logout'))

    assert response.status_code == 302
    assert '_auth_user_id' not in client.session


def test_account_and_order_pages_are_owner_only(
    client, buyer, other_user, product, make_order,
):
    own = make_order()
    foreign = make_order(owner=other_user)
    client.force_login(buyer)

    response = client.get(reverse('users:account'))

    assert response.status_code == 200
    assert list(response.context['orders']) == [own]

    assert client.get(reverse(
        'orders:order_confirmation', args=[own.pk],
    )).status_code == 200

    assert client.get(reverse(
        'orders:order_confirmation', args=[foreign.pk],
    )).status_code == 404

    assert client.post(reverse(
        'orders:order_cancel', args=[foreign.pk],
    )).status_code == 404

    cancel_url = reverse('orders:order_cancel', args=[own.pk])

    assert client.get(cancel_url).status_code == 405
    assert client.post(cancel_url).status_code == 302

    own.refresh_from_db()
    foreign.refresh_from_db()
    product.refresh_from_db()

    assert own.status == OrderStatus.CANCELLED
    assert foreign.status == OrderStatus.PENDING
    assert product.stock == 8


# Catalog

def test_catalog_filters_and_search(client, product):
    equipment = Category.objects.create(name='Equipment')

    kit = Product.objects.create(
        name='Starter kit',
        description='Useful equipment',
        category=equipment,
        price=Decimal('20.00'),
        stock=10,
        image='products/test.jpg',
    )
    budget = Product.objects.create(
        name='Budget product',
        description='Basic supplies',
        category=product.category,
        price=Decimal('0.00'),
        stock=10,
        image='products/test.jpg',
    )

    queries = [
        ({'categories': product.category.slug}, {product.pk, budget.pk}),
        ({'min_price': 5, 'max_price': 15}, {product.pk}),
        ({'min_price': 0, 'max_price': 0}, {budget.pk}),
        ({'search': 'starter'}, {kit.pk}),
        ({'search': 'roasted'}, {product.pk}),
    ]

    for query, expected_ids in queries:
        response = client.get(reverse('products:product_list'), query)

        assert response.status_code == 200
        assert {
            p.pk for p in response.context['products']
        } == expected_ids


def test_catalog_sorting_and_pagination(client, product):
    products = [product]

    for number in range(1, 8):
        products.append(Product.objects.create(
            name=f'Product {number}',
            description='Test',
            category=product.category,
            price=Decimal(number),
            stock=10,
            image='products/test.jpg',
        ))

    url = reverse('products:product_list')
    ascending = sorted(products, key=lambda p: p.price)

    for sorting, expected in [
        ('price', ascending),
        ('-price', list(reversed(ascending))),
        ('-created_at', list(reversed(products))),
    ]:
        response = client.get(url, {'sorting': sorting})

        assert response.status_code == 200
        assert response.context['paginator'].count == 8
        assert list(response.context['products']) == expected[:6]

    response = client.get(url, {'sorting': 'price', 'page': 2})
    assert list(response.context['products']) == ascending[6:]


def test_popularity_counts_only_completed_sales(client, product, make_order):
    rival = Product.objects.create(
        name='Rival',
        description='Test',
        category=product.category,
        price=Decimal('15.00'),
        stock=20,
        image='products/test.jpg',
    )

    for quantity, status in [
        (1, OrderStatus.PAID),
        (2, OrderStatus.SHIPPED),
        (3, OrderStatus.DELIVERED),
        (3, OrderStatus.PENDING),
    ]:
        make_order(quantity=quantity, status=status)

    cancelled = make_order(quantity=1)
    cancel_order(order_id=cancelled.pk, actor=cancelled.owner)

    make_order(item=rival, quantity=10)
    make_order(item=rival, quantity=1, status=OrderStatus.PAID)

    response = client.get(
        reverse('products:product_list'),
        {'sorting': '-popularity'},
    )

    products = list(response.context['products'])

    assert [p.pk for p in products] == [product.pk, rival.pk]
    assert [p.popularity for p in products] == [6, 1]


# Reviews

def test_review_permissions_delivery_and_duplicate_protection(
    client, buyer, product, make_order,
):
    url = reverse('reviews:review_add', args=[product.slug])
    data = {'rating': 4, 'comment': 'Good'}

    response = client.post(url, data)

    assert response.status_code == 302
    assert reverse('users:login') in response.url
    assert not Review.objects.exists()

    client.force_login(buyer)
    response = client.post(url, data)

    assert response.status_code == 302
    assert not Review.objects.exists()

    order = make_order()
    response = client.post(url, data)

    assert response.status_code == 302
    assert not Review.objects.exists()
    assert any(
        m.level == ERROR for m in get_messages(response.wsgi_request)
    )

    for status in (
        OrderStatus.PAID,
        OrderStatus.SHIPPED,
        OrderStatus.DELIVERED,
    ):
        order.status = status
        order.save(update_fields=['status'])

    response = client.post(url, data)

    assert response.status_code == 302
    assert any(
        m.level == SUCCESS for m in get_messages(response.wsgi_request)
    )

    review = Review.objects.get()
    assert review.owner == buyer
    assert review.product == product
    assert review.rating == 4

    response = client.post(url, {
        'rating': 1,
        'comment': 'Duplicate',
    })

    assert response.status_code == 302
    assert Review.objects.count() == 1

    review.refresh_from_db()
    assert review.rating == 4
    assert any(
        m.level == ERROR for m in get_messages(response.wsgi_request)
    )


def test_rating_validation_in_form_and_model(
    client, buyer, product, make_order,
):
    make_order(status=OrderStatus.DELIVERED)
    client.force_login(buyer)

    for rating in (0, 6, '1.5'):
        with pytest.raises(ValidationError):
            Review(
                owner=buyer,
                product=product,
                rating=rating,
            ).full_clean()

        response = client.post(
            reverse('reviews:review_add', args=[product.slug]),
            {'rating': rating},
        )

        assert response.status_code == 302
        assert not Review.objects.exists()


def test_product_average_rating_and_no_reviews(
    client, buyer, other_user, product, make_order,
):
    detail_url = reverse(
        'products:product_details',
        args=[product.slug],
    )

    response = client.get(detail_url)

    assert response.status_code == 200
    assert response.context['product'].average_rating is None
    assert b'No ratings yet.' in response.content

    make_order(status=OrderStatus.DELIVERED, quantity=1)
    make_order(
        owner=other_user,
        status=OrderStatus.DELIVERED,
        quantity=1,
    )

    Review.objects.create(
        owner=buyer,
        product=product,
        rating=3,
        comment='Useful product',
    )
    Review.objects.create(
        owner=other_user,
        product=product,
        rating=5,
        comment='Excellent quality',
    )

    response = client.get(detail_url)

    assert response.context['product'].average_rating == 4
    assert response.context['product'].reviews.count() == 2
    assert b'Useful product' in response.content
    assert b'Excellent quality' in response.content

    response = APIClient().get(
        reverse('api-product-detail', args=[product.pk]),
    )

    assert response.status_code == 200
    assert response.data['average_rating'] == 4


# REST API

def test_public_product_api_filters_validation_and_pagination(product):
    client = APIClient()
    url = reverse('api-product-list')

    for query in [
        {'min_price': -1},
        {'max_price': 'invalid'},
        {'min_price': 20, 'max_price': 10},
        {'category': 'invalid'},
    ]:
        assert client.get(url, query).status_code == 400

    equipment = Category.objects.create(name='Equipment')

    kit = Product.objects.create(
        name='Starter kit',
        description='Useful equipment',
        category=equipment,
        price=Decimal('20.00'),
        stock=10,
        image='products/test.jpg',
    )
    budget = Product.objects.create(
        name='Budget product',
        description='Basic supplies',
        category=product.category,
        price=Decimal('0.00'),
        stock=10,
        image='products/test.jpg',
    )
    hidden = Product.objects.create(
        name='Hidden product',
        description='Roasted ingredients',
        category=product.category,
        price=Decimal('10.00'),
        stock=10,
        image='products/test.jpg',
        is_active=False,
    )

    queries = [
        ({'category': product.category_id}, {product.pk, budget.pk}),
        ({'min_price': 5, 'max_price': 15}, {product.pk}),
        ({'min_price': 0, 'max_price': 0}, {budget.pk}),
        ({'search': 'starter'}, {kit.pk}),
        ({'search': 'roasted'}, {product.pk}),
    ]

    for query, expected_ids in queries:
        response = client.get(url, query)

        assert response.status_code == 200
        assert {
            p['id'] for p in response.data['results']
        } == expected_ids

    response = client.get(
        reverse('api-product-detail', args=[product.pk]),
    )

    assert response.status_code == 200
    assert response.data['average_rating'] is None

    assert client.get(
        reverse('api-product-detail', args=[hidden.pk]),
    ).status_code == 404

    for number in range(5):
        Product.objects.create(
            name=f'API product {number}',
            description='Test',
            category=product.category,
            price=Decimal('5.00'),
            stock=10,
            image='products/test.jpg',
        )

    response = client.get(url)

    assert response.data['count'] == 8
    assert len(response.data['results']) == 6

    response = client.get(url, {'page': 2})
    assert len(response.data['results']) == 2


def test_jwt_login_refresh_and_protected_orders(buyer, order_data):
    client = APIClient()
    orders_url = reverse('api-order-list')

    assert client.get(orders_url).status_code == 401
    assert client.post(
        orders_url, order_data, format='json',
    ).status_code == 401

    token_url = reverse('token_obtain_pair')

    response = client.post(token_url, {
        'username': buyer.username,
        'password': 'incorrect',
    }, format='json')

    assert response.status_code == 401

    response = client.post(token_url, {
        'username': buyer.username,
        'password': PASSWORD,
    }, format='json')

    assert response.status_code == 200

    tokens = response.data
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
    )

    assert client.get(orders_url).status_code == 200

    response = client.post(reverse('token_refresh'), {
        'refresh': tokens['refresh'],
    }, format='json')

    assert response.status_code == 200

    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {response.data['access']}",
    )
    assert client.get(orders_url).status_code == 200


def test_api_creates_order_with_server_prices(
    api_client, buyer, product, order_data,
):
    response = api_client.post(
        reverse('api-order-list'),
        order_data,
        format='json',
    )

    assert response.status_code == 201

    order = Order.objects.get()

    assert order.owner == buyer
    assert order.status == OrderStatus.PENDING
    assert order.total_price == Decimal('20.00')
    assert order.items.get().price == Decimal('10.00')
    assert response.data['id'] == order.pk
    assert Decimal(response.data['total_price']) == Decimal('20.00')

    product.refresh_from_db()
    assert product.stock == 8


def test_api_rejects_invalid_data_and_client_controlled_fields(
    api_client, product, order_data,
):
    url = reverse('api-order-list')

    for field, value in {
        'user': 1,
        'owner': 1,
        'price': '0.01',
        'total_price': '0.01',
        'status': 'paid',
    }.items():
        response = api_client.post(
            url,
            {**order_data, field: value},
            format='json',
        )

        assert response.status_code == 400
        assert field in response.data

    data = {
        **order_data,
        'items': [{
            'product_id': product.pk,
            'quantity': 2,
            'price': '0.01',
        }],
    }

    assert api_client.post(
        url, data, format='json',
    ).status_code == 400

    assert not Order.objects.exists()

    product.refresh_from_db()
    assert product.stock == 10

    for items in [
        [],
        [{'product_id': product.pk, 'quantity': 0}],
        [{'product_id': product.pk, 'quantity': 11}],
    ]:
        response = api_client.post(
            url,
            {**order_data, 'items': items},
            format='json',
        )

        assert response.status_code == 400
        assert not Order.objects.exists()

        product.refresh_from_db()
        assert product.stock == 10


def test_api_orders_are_owner_only(api_client, other_user, make_order):
    own = make_order()
    foreign = make_order(owner=other_user)

    response = api_client.get(reverse('api-order-list'))

    assert response.status_code == 200
    assert [
        order['id'] for order in response.data['results']
    ] == [own.pk]

    assert api_client.get(reverse(
        'api-order-detail', args=[own.pk],
    )).status_code == 200

    assert api_client.get(reverse(
        'api-order-detail', args=[foreign.pk],
    )).status_code == 404

    assert api_client.post(reverse(
        'api-order-cancel', args=[foreign.pk],
    )).status_code == 404

    foreign.refresh_from_db()
    assert foreign.status == OrderStatus.PENDING


def test_api_cancellation_and_forbidden_methods(
    api_client, product, make_order,
):
    order = make_order()
    detail_url = reverse('api-order-detail', args=[order.pk])

    for method in ('put', 'patch', 'delete'):
        response = getattr(api_client, method)(
            detail_url, {}, format='json',
        )
        assert response.status_code == 405

    cancel_url = reverse('api-order-cancel', args=[order.pk])

    assert api_client.get(cancel_url).status_code == 405
    assert api_client.post(cancel_url).status_code == 200
    assert api_client.post(cancel_url).status_code == 400

    order.refresh_from_db()
    product.refresh_from_db()

    assert order.status == OrderStatus.CANCELLED
    assert product.stock == 10

    paid = make_order(status=OrderStatus.PAID)

    assert api_client.post(reverse(
        'api-order-cancel', args=[paid.pk],
    )).status_code == 400

    paid.refresh_from_db()
    product.refresh_from_db()

    assert paid.status == OrderStatus.PAID
    assert product.stock == 8


def test_api_documentation_and_schema_load(client):
    assert client.get(reverse('api-docs')).status_code == 200

    response = client.get(
        reverse('api-schema'),
        HTTP_ACCEPT='application/vnd.oai.openapi+json',
    )

    assert response.status_code == 200
    assert '/api/orders/' in response.json()['paths']

NEW_PASSWORD = 'FreshSecurePassword73!'


@pytest.fixture
def password_change_data():
    return {
        'old_password': PASSWORD,
        'new_password1': NEW_PASSWORD,
        'new_password2': NEW_PASSWORD,
    }



def test_api_password_change_requires_authentication(
    buyer, password_change_data,
):
    original_hash = buyer.password

    response = APIClient().post(
        reverse('api_password_change'),
        password_change_data,
        format='json',
    )

    assert response.status_code == 401
    buyer.refresh_from_db()
    assert buyer.password == original_hash



def test_api_password_change_success(
    api_client, buyer, other_user, password_change_data,
):
    other_hash = other_user.password

    response = api_client.post(
        reverse('api_password_change'),
        password_change_data,
        format='json',
    )

    assert response.status_code == 200

    buyer.refresh_from_db()
    other_user.refresh_from_db()
    assert buyer.check_password(NEW_PASSWORD)
    assert not buyer.check_password(PASSWORD)
    assert other_user.password == other_hash



def test_api_password_change_rejects_wrong_old_password(
    api_client, buyer, password_change_data,
):
    original_hash = buyer.password
    password_change_data['old_password'] = 'WrongPassword!'

    response = api_client.post(
        reverse('api_password_change'),
        password_change_data,
        format='json',
    )

    assert response.status_code == 400
    assert 'old_password' in response.data

    buyer.refresh_from_db()
    assert buyer.password == original_hash



def test_api_password_reset_flow(buyer, mailoutbox):
    buyer.email = 'buyer@example.com'
    buyer.save(update_fields=['email'])
    client = APIClient()

    response = client.post(
        reverse('api_reset_password'),
        {'email': buyer.email},
        format='json',
    )

    assert response.status_code == 200
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [buyer.email]

    link = re.search(
        r'/password_reset_confirm/([^/]+)/([^/]+)/',
        mailoutbox[0].body,
    )
    assert link is not None

    data = {
        'uidb64': link.group(1),
        'token': link.group(2),
        'new_password1': NEW_PASSWORD,
        'new_password2': NEW_PASSWORD,
    }
    url = reverse('api_reset_password_confirm')

    response = client.post(url, data, format='json')
    assert response.status_code == 200

    buyer.refresh_from_db()
    assert buyer.check_password(NEW_PASSWORD)
    assert not buyer.check_password(PASSWORD)
    changed_hash = buyer.password

    assert client.post(url, data, format='json').status_code == 400

    buyer.refresh_from_db()
    assert buyer.password == changed_hash



def test_api_password_reset_unknown_email(buyer, mailoutbox):
    buyer.email = 'buyer@example.com'
    buyer.save(update_fields=['email'])
    client = APIClient()
    url = reverse('api_reset_password')

    known = client.post(url, {'email': buyer.email}, format='json')
    mailoutbox.clear()

    unknown = client.post(
        url,
        {'email': 'unknown@example.com'},
        format='json',
    )

    assert known.status_code == unknown.status_code == 200
    assert known.data == unknown.data
    assert len(mailoutbox) == 0



def test_api_password_reset_rejects_invalid_token(buyer):
    original_hash = buyer.password

    response = APIClient().post(
        reverse('api_reset_password_confirm'),
        {
            'uidb64': urlsafe_base64_encode(force_bytes(buyer.pk)),
            'token': 'invalid-token',
            'new_password1': NEW_PASSWORD,
            'new_password2': NEW_PASSWORD,
        },
        format='json',
    )

    assert response.status_code == 400

    buyer.refresh_from_db()
    assert buyer.password == original_hash