from django import forms

from betting.models import BetScope, Club, DepositWithdrawMethod, ConfigModel


class BetScopeForm(forms.ModelForm):
    class Meta:
        model = BetScope
        fields = ('question', 'end_time',
                  'option_1', 'option_1_rate',
                  'option_2', 'option_2_rate',
                  'option_3', 'option_3_rate',
                  'option_4', 'option_4_rate',
                  )


class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ('name', 'admin', 'balance', 'username', 'password', 'club_commission')


class MethodForm(forms.ModelForm):
    class Meta:
        model = DepositWithdrawMethod
        fields = ('code', 'number1', 'number2')


class ConfigForm(forms.ModelForm):
    class Meta:
        model = ConfigModel
        fields = ('name', 'value',)
