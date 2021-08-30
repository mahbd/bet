import json
from random import randint

from django import template
from django.core.serializers import serialize
from django.db.models import Sum

from betting.models import BetScope, BET_CHOICES, Match
from betting.views import get_last_bet

register = template.Library()


@register.inclusion_tag('easy_admin/easy_table.html')
def easy_table(table_data):
    return table_data


@register.inclusion_tag('easy_admin/easy_table.html')
def user_list_table_club(users):
    table_header = (
        ('', 'ID'),
        ('', 'Joining Date'),
        ('', 'Last Bet'),
        ('', 'Name'),
        ('', 'Username'),
        ('', 'Total Bet'),
        ('', 'Commission'),
    )
    table_body = [
        (user.id, user.userclubinfo.date_joined, get_last_bet(user) and get_last_bet(user).created_at, user.get_full_name(),
         user.username, user.userclubinfo.total_bet, user.userclubinfo.total_commission) for user in users]
    table_data = {
        'table_header': table_header,
        'table_body': table_body,
    }
    return table_data


@register.inclusion_tag('easy_admin/easy_table.html')
def match_detail_table(match: Match):
    table_body = [(' '.join(key.split('_')).title(), value)
                  for key, value in json.loads(serialize('json', [match]))[0]['fields'].items()]
    table_data = {
        'table_body': table_body,
    }
    return table_data


@register.inclusion_tag('easy_admin/easy_table.html')
def bet_option_table_sm(scope: BetScope):
    table_header = (
        ('', 'Type'),
        ('', 'Option 1'),
        ('', 'Option 2'),
        ('', 'Option 3'),
        ('', 'Option 4'),
    )
    table_body = [('Options', scope.option_1, scope.option_2, scope.option_3, scope.option_4),
                  ('Rate', scope.option_1_rate, scope.option_2_rate, scope.option_3_rate, scope.option_4_rate)]
    table_data = {
        'table_header': table_header,
        'table_body': table_body,
    }
    return table_data


def sum_filter_bet_set(bet_scope, choice, field='winning'):
    return bet_scope.bet_set.filter(choice=choice).aggregate(Sum(field))[f'{field}__sum'] or 0


@register.inclusion_tag('easy_admin/easy_table.html')
def bet_option_table_detail(bet_scope: BetScope):
    table_header = (
        ('', 'Type'),
        ('', 'Option 1'),
        ('', 'Option 2'),
        ('', 'Option 3'),
        ('', 'Option 4'),
    )
    option1_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[0][0], 'amount')
    option2_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[1][0], 'amount')
    option3_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[2][0], 'amount')
    option4_bet = sum_filter_bet_set(bet_scope, BET_CHOICES[3][0], 'amount')
    total_bet = option1_bet + option2_bet + option3_bet + option4_bet
    option1_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[0][0])
    option2_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[1][0])
    option3_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[2][0])
    option4_benefit = total_bet - sum_filter_bet_set(bet_scope, BET_CHOICES[3][0])

    table_body = [('Options', bet_scope.option_1, bet_scope.option_2, bet_scope.option_3, bet_scope.option_4),
                  ('Rate', bet_scope.option_1_rate, bet_scope.option_2_rate, bet_scope.option_3_rate,
                   bet_scope.option_4_rate),
                  ('Total Bet', option1_bet, option2_bet, option3_bet, option4_bet),
                  ('Possible Revenue', option1_benefit, option2_benefit, option3_benefit, option4_benefit)
                  ]
    table_data = {
        'table_header': table_header,
        'table_body': table_body,
    }
    return table_data


@register.inclusion_tag('easy_admin/link_buttons_group.html')
def link_buttons_group(buttons):
    return {'buttons': buttons}


@register.inclusion_tag('easy_admin/enable_field_button.html')
def enable_f_button(field_id):
    return {'field_id': str(field_id)}


@register.filter
def join_s(a, b):
    return str(a) + str(b)


@register.filter(name='add_classes')
def add_classes(value, arg):
    """
    Add provided classes to form field
    :param value: form field
    :param arg: string of classes seperated by ' '
    :return: edited field
    """
    css_classes = value.field.widget.attrs.get('class', '')
    # check if class is set or empty and split its content to list (or init list)
    if css_classes:
        css_classes = css_classes.split(' ')
    else:
        css_classes = []
    # prepare new classes to list
    args = arg.split(' ')
    for a in args:
        if a not in css_classes:
            css_classes.append(a)
    # join back to single string
    return value.as_widget(attrs={'class': ' '.join(css_classes)})


@register.filter
def hide_field(value):
    return value.as_widget(attrs={'hidden': True})


@register.filter
def disable_field(value, field_id=randint(1, 1000000), args=''):
    classes = value.field.widget.attrs.get('class', '')
    if classes:
        classes = classes.split(' ')
    else:
        classes = []
    args = args.split(' ')
    classes = [*classes, *args]
    return value.as_widget(attrs={
        'disabled': True,
        'class': ' '.join(classes),
        'id': field_id,
    })


@register.filter
def readonly_field(value, field_id=randint(1, 1000000), args=''):
    classes = value.field.widget.attrs.get('class', '')
    if classes:
        classes = classes.split(' ')
    else:
        classes = []
    args = args.split(' ')
    classes = [*classes, *args]
    return value.as_widget(attrs={
        'readonly': True,
        'class': ' '.join(classes),
        'id': field_id,
    })


@register.inclusion_tag('easy_admin/disable_with_button.html')
def disable_with_button(field, classes='form-control'):
    field_id = randint(1, 1000000)
    return {'field': readonly_field(field, field_id, classes), 'id': field_id, 'label': field.label}


@register.inclusion_tag('easy_admin/two_dwb.html')
def double_rwb(field1, field2, classes='form-control'):
    id1 = randint(1, 1000000)
    id2 = randint(1, 1000000)
    return {
        'field1': readonly_field(field1, id1, classes), 'id1': id1, 'label1': field1.label,
        'field2': readonly_field(field2, id2, classes), 'id2': id2, 'label2': field2.label,
    }
