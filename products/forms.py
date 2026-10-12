from django import forms
from django.core.exceptions import ValidationError

class ProductPriceFilterForm(forms.Form):
    min_price = forms.DecimalField(min_value=0, required=False)
    max_price = forms.DecimalField(min_value=0, required=False)

    def clean(self):
        cleaned_data = super().clean()
        minimum = cleaned_data.get('min_price')
        maximum = cleaned_data.get('max_price')

        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValidationError('Minimum price is greater than maximum price')
        return cleaned_data
