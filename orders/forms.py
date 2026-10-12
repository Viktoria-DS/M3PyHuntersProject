import re

from django import forms
import logging

from orders.choices import PAYMENT_METHOD_CHOICES

class CartQuantityForm(forms.Form):
    product_slug = forms.SlugField()
    quantity = forms.IntegerField(min_value = 0)

class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=100, required=True)
    phone = forms.CharField(max_length=32, required=True)
    city = forms.CharField(max_length=100, required=True)
    shipping_address = forms.CharField(widget=forms.Textarea, required=True)
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES)

    def clean(self):
        cleaned_data = super().clean()
        logger = logging.getLogger(__name__)
        logger.debug(f"Cleaned data: {cleaned_data}")
        return cleaned_data

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        for separator in (' ', '(', ')', '-'):
            phone = phone.replace(separator, '')
        if not phone.startswith(('8', '+7')):
            raise forms.ValidationError('Phone number must start with 8 or +7')

        if not re.fullmatch(r'(8|\+7)[0-9]{10}', phone):
            raise forms.ValidationError(
                'Enter a phone number starting with 8 or +7, '
                'followed by 10 digits.'
            )

        if phone.startswith('8'):
            phone = '+7' + phone[1:]

        return phone