from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, \
    UsernameField

from users.models import User


class RegisterForm(UserCreationForm):
    avatar = forms.ImageField(required=False, widget=forms.FileInput(
        attrs={
            'class': 'Input', 'required': False, 'id': 'avatar',
            'name': 'avatar'
        })
    )


    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1',
                  'password2', 'avatar')

        widgets = {
            'username': forms.TextInput(
                attrs={
                    'class': 'Input', 'placeholder': 'Username',
                    'required': True, 'id': 'username', 'name': 'username'
                }),
            'email': forms.EmailInput(
                attrs={
                    'class': 'Input', 'placeholder': 'Email',
                    'required': True, 'id': 'email', 'name': 'email'
                }
            ),
            'first_name': forms.TextInput(
                attrs={
                    'class': 'Input', 'placeholder': 'First Name',
                    'required': True, 'id': 'first_name', 'name': 'first_name'
                }
            ),
            'last_name': forms.TextInput(
                attrs={
                    'class': 'Input', 'placeholder': 'Last Name',
                    'required': True, 'id': 'last_name', 'name': 'last_name'
                }
            ),
            'password': forms.PasswordInput(
                attrs={
                    'class': 'Input', 'placeholder': 'Password',
                    'required': True, 'id': 'password', 'name': 'password'
                }
            ),
            'password2': forms.PasswordInput(
                attrs={
                    'class': 'Input', 'placeholder': 'Password again',
                    'required': True, 'id': 'password2', 'name': 'password2'
                }
            ),
            'avatar': forms.FileInput(
                attrs={
                    'class': 'Input', 'required': False, 'id': 'avatar', 'name': 'avatar'
                }
            )

        }

class LoginForm(AuthenticationForm):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """

    username = UsernameField(widget=forms.TextInput(
        attrs={
            "autofocus": True, 'class': 'Input', 'placeholder': 'Username',
            'required': True, 'id': 'username', 'name': 'username'
        }))
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'Input', 'placeholder': 'Password',
                'required': True, 'id': 'password', 'name': 'password',
                "autocomplete": "current-password"
            }),
    )


class UpdateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('avatar', 'first_name', 'last_name', 'email', 'city',
                  'address', 'phone')