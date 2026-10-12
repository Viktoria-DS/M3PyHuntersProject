from django.urls import path

from reviews.apps import ReviewsConfig
from reviews.views import ReviewCreateView

app_name = ReviewsConfig.name
urlpatterns = [path('<slug:slug>/add/', ReviewCreateView.as_view(), name='review_add'),]