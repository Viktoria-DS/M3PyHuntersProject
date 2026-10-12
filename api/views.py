
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Avg
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, extend_schema_view, inline_serializer
from rest_framework import viewsets, filters, mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import filters, serializers, viewsets
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from api.serializers import ProductSerializer, OrderSerializer, OrderCreateSerializer, PasswordResetRequestSerializer, \
    PasswordResetConfirmSerializer, PasswordChangeSerializer
from orders.models import Order
from orders.services import cancel_order
from products.forms import ProductPriceFilterForm
from products.models import Product

@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by category ID.',
                required=False,
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description='Minimum price. Must be at least zero.',
                required=False,
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description='Maximum price. Must be at least zero.',
                required=False,
            ),
        ],
    ),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (Product.objects. filter(is_active=True).annotate(average_rating=Avg('reviews__rating')).order_by('-created_at', 'pk'))
    serializer_class = ProductSerializer
    permission_classes = AllowAny,
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        queryset = super().get_queryset()
        price_form = ProductPriceFilterForm(self.request.query_params)

        if not price_form.is_valid():
            raise ValidationError({
                field: list(errors)
                for field, errors in price_form.errors.items()
            })

        minimum = price_form.cleaned_data.get('min_price')
        maximum = price_form.cleaned_data.get('max_price')
        if minimum is not None:
            queryset = queryset.filter(price__gte=minimum)
        if maximum is not None:
            queryset = queryset.filter(price__lte=maximum)

        category = self.request.query_params.get('category')
        if category is not None:
            category_id = serializers.IntegerField(min_value=1).run_validation(category)
            queryset = queryset.filter(category_id=category_id)

        return queryset


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return (Order.objects. filter(owner = self.request.user).prefetch_related('items').order_by('-created_at', '-pk'))

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    @extend_schema(
        request=OrderCreateSerializer,
        responses={201: OrderSerializer},
        examples=[
            OpenApiExample(
                'Create an order',
                value={
                    'items': [
                        {'product_id': 1, 'quantity': 2},
                    ],
                    'shipping_address': 'Example street 12, Berlin',
                    'payment_method': 'cod',
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        response_serializer = OrderSerializer(order, context = self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


    @extend_schema(
        request=None,
        responses={200: OrderSerializer},
    )
    @action(detail=True, methods=['post'])

    def cancel(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            canceled_order = cancel_order(
                order_id = order.pk,
                actor = request.user,
            )
        except DjangoValidationError as error:
            if hasattr(error, 'message_dict'):
                error_dict = error.message_dict
            else:
                error_dict = error.messages
            raise ValidationError(error_dict)
        serializer = self.get_serializer(canceled_order)
        return Response(serializer.data)

@extend_schema(
    request = PasswordResetRequestSerializer,
    responses={200: inline_serializer(
        name = 'PasswordResetRequestResponsse',
        fields = {'detail': serializers.CharField()})
    },
)

class PasswordResetRequestView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_form = PasswordResetForm(data = serializer.validated_data)
        if not reset_form.is_valid():
            raise ValidationError(reset_form.errors)

        reset_form.save(
            request = self.request,
            use_https=request.is_secure(),
            email_template_name = 'users/reset_password_email.txt',
        )

        return Response({'detail': 'If an account exists with this email address, you will receive password-reset instructions.'}, status=status.HTTP_200_OK)

@extend_schema(
    request=PasswordResetConfirmSerializer,
    responses={200: inline_serializer(
        name = 'PasswordResetConfirmResponse',
        fields = {'detail': serializers.CharField()}
    )}
)
class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        User = get_user_model()
        try:
            uid = urlsafe_base64_decode(data['uidb64']).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError("This reset link is invalid or has expired.”")

        if not default_token_generator.check_token(user, data['token']):
            raise ValidationError("This reset link is invalid or has expired.")

        form = SetPasswordForm(user, data=data)
        if not form.is_valid():
            raise ValidationError(form.errors)
        form.save()
        return Response({'detail': 'Your password was successfully changed!'})

@extend_schema(
        request=PasswordChangeSerializer,
        responses={
            200: inline_serializer(
                name='PasswordChangeResponse',
                fields={'detail': serializers.CharField()},
            ),
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
    )
class PasswordChangeAPIView(GenericAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        form = PasswordChangeForm(
            user=request.user,
            data=serializer.validated_data,
        )
        if not form.is_valid():
            raise ValidationError(form.errors)

        form.save()
        return Response(
            {'detail': 'Password changed successfully.'},
            status=status.HTTP_200_OK,
        )
