from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    product = models.ForeignKey('products.Product',
                                on_delete=models.CASCADE,
                                related_name='reviews')
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    heading = models.CharField(max_length=100, blank=True, null=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(max_length=1000, blank=True, null=True)
    image = models.ImageField(upload_to='reviews/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.owner} - {self.product}: {self.rating}'

    def get_absolute_url(self):
        return f'/reviews/{self.id}'
    def get_stars(self):
        return range(int(self.rating))

    def get_empty_stars(self):
        return range(5 - len(self.get_stars()))