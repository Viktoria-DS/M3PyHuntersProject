from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/products/category/{self.slug}'

    def get_products(self):
        return self.products.all()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, db_index=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT,
                                 related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(0)])
    specifications = models.JSONField(default=dict, blank=True, null=True)
    image = models.ImageField(upload_to='products/')
    is_active = models.BooleanField(default=True)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/products/{self.slug}'

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition = models.Q(price__gte=0),
                name = "product_price_nonnegative"
            ),
            models.CheckConstraint(
                condition = models.Q(stock__gte=0),
                name = "product_stock_nonnegative"
            )
        ]