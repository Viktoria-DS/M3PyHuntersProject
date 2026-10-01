from django import forms
import logging

class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=100, required=True)
    phone = forms.CharField(max_length=15, required=True)
    city = forms.CharField(max_length=100, required=True)
    shipping_address = forms.CharField(widget=forms.Textarea, required=True)
    payment_method = forms.ChoiceField(choices=[
        ('debit', 'Debit Card'),
        ('wallet', 'Digital Wallet'),
        ('cod', 'Cash On Delivery')
    ])

    def clean(self):
        cleaned_data = super().clean()
        logger = logging.getLogger(__name__)
        logger.debug(f"Cleaned data: {cleaned_data}")
        return cleaned_data

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not phone.startswith('8') or phone.startswith('+7'):
            raise forms.ValidationError('Phone number must start with 8 or +7')
        return phone