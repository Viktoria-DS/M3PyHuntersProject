from rest_framework import serializers

from orders.models import Order, OrderItem
from products.models import Product
from django.core.exceptions import ValidationError as DjangoValidationError

from orders.choices import PAYMENT_METHOD_CHOICES
from orders.services import create_order

class ProductSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(
        read_only=True,
        allow_null = True,
    )

    class Meta:
        model = Product
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['id', 'order', 'product', 'quantity', 'price', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = '__all__'

class StrictInputSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown_fields = set(data) - set(self.fields)

            if unknown_fields:
                raise serializers.ValidationError({
                    field: 'This field is not allowed.'
                    for field in sorted(unknown_fields)
                })

        return super().to_internal_value(data)


class OrderCreateItemSerializer(StrictInputSerializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(StrictInputSerializer):
    items = OrderCreateItemSerializer(
        many=True,
        allow_empty=False,
    )
    shipping_address = serializers.CharField()
    payment_method = serializers.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
    )

    def create(self, validated_data):
        try:
            return create_order(
                owner=self.context['request'].user,
                **validated_data,
            )
        except DjangoValidationError as error:
            if hasattr(error, 'message_dict'):
                detail = error.message_dict
            else:
                detail = error.messages

            raise serializers.ValidationError(detail) from error

class PasswordResetRequestSerializer(StrictInputSerializer):
    email = serializers.EmailField(max_length=254)


class PasswordResetConfirmSerializer(StrictInputSerializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password1 = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, trim_whitespace=False)

class PasswordChangeSerializer(StrictInputSerializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password1 = serializers.CharField( write_only=True, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, trim_whitespace=False)