from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, \
    PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetCompleteView
from django.urls import path, reverse_lazy

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
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('account/', AccountView.as_view(), name='account'),
    path('update/<int:pk>', UpdateUserView.as_view(), name='update_user'),
    path('change-password/', PasswordChangeView.as_view(
        template_name='users/change_password.html',
        success_url=reverse_lazy('users:account')
    ), name='password_change'),
    path('forgot_password/', PasswordResetView.as_view(
        template_name="users/reset_password.html",
        success_url=reverse_lazy('users:password_reset_done'),
        email_template_name='users/reset_password_email.txt',
    ), name='forgot_password'),
    path('password_reset_confirm/<str:uidb64>/<str:token>/',
         PasswordResetConfirmView.as_view(
             template_name="users/reset_password_confirm.html",
         success_url=reverse_lazy('users:password_reset_complete'),),
         name='reset_password_confirm'),
    path(
        'password_reset_done/', PasswordResetDoneView.as_view(template_name='users/reset_password_done.html', ),
        name='password_reset_done'
    ),
    path("reset_password_complete/", PasswordResetCompleteView.as_view(
        template_name='users/reset_password_complete.html',

    ), name='password_reset_complete'
         ),
]
