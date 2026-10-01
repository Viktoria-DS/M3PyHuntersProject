from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView

from orders.models import Order
from users.forms import RegisterForm, UpdateUserForm
from users.models import User


class RegisterView(CreateView):
    model = User
    form_class = RegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')


class UpdateUserView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UpdateUserForm
    success_url = reverse_lazy('users:account')

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def get(self, *args, **kwargs):
        raise NotImplementedError


class AccountView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'users/account.html'
    success_url = reverse_lazy('users:account')
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(owner=self.request.user)