from django import forms

from betting.models import Transaction


class DepositForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['user', 'amount', 'transaction_id', 'account', 'superuser_account', 'verified']


class WithdrawForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['user', 'amount', 'transaction_id', 'account', 'superuser_account', 'verified']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.TextInput(attrs={'class': 'form-control'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'account': forms.TextInput(attrs={'class': 'form-control'}),
            'superuser_account': forms.TextInput(attrs={'class': 'form-control'}),
            'verified': forms.HiddenInput(),
        }


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['user', 'amount', 'to', 'verified']
