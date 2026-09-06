from django.contrib import admin


from reviews.models import Review


# Register your models here.
@admin.register(Review)

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('owner', 'product', 'rating', 'created_at', 'updated_at')
    list_filter = ('owner', 'product', 'rating')
    search_fields = ('owner__username', 'product__name')
    readonly_fields = ('created_at', 'updated_at')