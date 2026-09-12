from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Avg
from django.utils.text import slugify


# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    def get_absolute_url(self):
        return f'/products/category/{self.slug}/'
    def get_products(self):
        return self.products.all()
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save()

    class Meta:
        verbose_name_plural = 'Categories'
        verbose_name = 'Category'

class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    price = models.DecimalField(decimal_places=2, max_digits=10, validators=[MinValueValidator(0.0)])
    image = models.ImageField(upload_to='products/')
    is_active = models.BooleanField(default=True)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_rating(self):
        if self.reviews.count() > 0:
            return self.reviews.aggregate(Avg('rating'))['rating__avg']
        return None

    def __str__(self):
        return self.name
    def get_absolute_url(self):
        return f'/products/{self.slug}/'
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save()

    class Meta:
        verbose_name_plural = 'Products'
        verbose_name = 'Product'
        ordering = ['-created_at']