from django import forms
from .models import CustomUser
from django_bootstrap5.widgets import RadioSelect
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser



class UserLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'username'}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'password'}
        )
    )



class UserRegistrationForm(UserCreationForm):
    """
    Form for user registration with account type selection.
    """
    email = forms.EmailField(required=True)
    phonenumber = forms.CharField(max_length=50, required=True)
    account_type = forms.ChoiceField(
        required=True,
        widget=RadioSelect(attrs={'class': 'form-control col'}),
        choices=((1, 'Seller'), (2, 'Buyer')),
        initial=2,
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phonenumber', 'password1', 'password2', 'account_type']

    def clean_email(self):
        """
        Validate that the email is unique.
        """
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("This email is already in use.")
        return email

    def clean_phonenumber(self):
        """
        Validate that the phone number is unique.
        """
        phonenumber = self.cleaned_data.get('phonenumber')
        if CustomUser.objects.filter(phonenumber=phonenumber).exists():
            raise ValidationError("This phone number is already in use.")
        return phonenumber

    def save(self, commit=True):
        """
        Save the user and set their account type (is_seller or not).
        """
        user = super().save(commit=False)
        account_type = self.cleaned_data.get('account_type')
        if account_type == '1':  # Seller
            user.is_seller = True
        else:  # Buyer
            user.is_seller = False
        if commit:
            user.save()
        return user


class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email']
