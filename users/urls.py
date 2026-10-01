from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, include

from users.apps import UsersConfig
from users.forms import LoginForm
from users.views import RegisterView, AccountView, UpdateUserView

app_name = UsersConfig.name

urlpatterns = [
    # login, logout, register
    path('login/', LoginView.as_view(
        template_name='users/login.html',
        form_class=LoginForm,
        success_url='/'
    ), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('account/', AccountView.as_view(), name='account'),
    path('update/<int:pk>', UpdateUserView.as_view(), name='update_user'),
]