from typing import Type, Union

from django.db import DataError
from django.db.models import Model, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from betting.views import get_config_from_model
from users.models import User


def qs_exists(queryset):
    try:
        return queryset.exists()
    except (TypeError, ValueError, DataError):
        return False


def count_limit_validator(user: User, model, des, md=0):
    limit_count = int(get_config_from_model(f'limit_{des}'))
    total_today = model.objects.filter(user=user, created_at__day=timezone.now().day).count()
    if total_today >= limit_count + md:
        raise ValidationError(f"Maximum limit of {limit_count} per day exceed. {total_today}")


class UniqueMultiQuerysetValidator(UniqueValidator):
    """
    Validator that corresponds to `unique=True` on a model field.

    Should be applied to an individual field on the serializer.
    """
    message = 'This field must be unique.'
    requires_context = True

    def __init__(self, queryset1, queryset2, message=None, lookup='exact'):
        super().__init__(queryset1, message, lookup)
        self.queryset1 = queryset1
        self.queryset2 = queryset2
        self.message = message or self.message
        self.lookup = lookup

    def exclude_current_instance(self, queryset, instance):
        if instance is not None:
            queryset2 = queryset.filter(pk=instance.pk)
            if queryset2:
                if queryset2.first().__class__ == instance.__class__:
                    return queryset.exclude(pk=instance.pk)
        return queryset

    def __call__(self, value, serializer_field):
        # Determine the underlying model field name. This may not be the
        # same as the serializer field name if `source=<>` is set.
        field_name = serializer_field.source_attrs[-1]
        # Determine the existing instance, if this is an update operation.
        instance = getattr(serializer_field.parent, 'instance', None)

        queryset1 = self.queryset1
        queryset2 = self.queryset2
        queryset1 = self.filter_queryset(value, queryset1, field_name)
        queryset2 = self.filter_queryset(value, queryset2, field_name)
        queryset1 = self.exclude_current_instance(queryset1, instance)
        if qs_exists(queryset1) or qs_exists(queryset2):
            raise ValidationError(self.message, code='unique')


class BetQuestionValidator:
    def __call__(self, value, *args, **kwargs):
        if value.is_locked():
            raise ValidationError('Bet Question is locked or closed')


class QuestionOptionValidator:
    def __init__(self, model):
        self.model = model

    def __call__(self, value, *args, **kwargs):
        total_bet = self.model.objects.filter(choice=value).aggregate(Sum('amount'))['amount__sum'] or 0
        if total_bet >= value.limit:
            raise ValidationError('Bet limit for this option exceeded')


class CountLimitValidator:
    def __init__(self, des: str, model: Type[Model], limit: Union[int, callable] = None, when='day',
                 field_time='created_at', field_check='user'):
        self.des = des
        self.model = model
        self.when = when
        self.field_time = field_time
        self.field_check = field_check
        self.limit = limit() if callable(limit) else limit

    def generate_query_params(self, value):
        query = {}
        if self.when == 'day':
            query[f'{self.field_time}__day'] = timezone.now().day
        elif self.when == 'month':
            query[f'{self.field_time}__month'] = timezone.now().month
        elif self.when == 'year':
            query[f'{self.field_time}__year'] = timezone.now().year
        query[self.field_check] = value
        return query

    def __call__(self, value, **kwargs):
        limit_count = int(get_config_from_model(f'limit_{self.des}'))
        query = self.generate_query_params(value)
        total_count = self.model.objects.filter(**query).count()
        if total_count > limit_count:
            raise ValidationError(f"Maximum limit of {limit_count} per day exceed. {total_count}")


class MaximumLimitValidator:
    def __init__(self, des):
        self.des = des

    def __call__(self, value, *args, **kwargs):
        maximum = int(get_config_from_model(f'max_{self.des}'))
        if value > maximum:
            raise ValidationError(f"{value} exceed maximum {maximum} limit of {self.des}")


class MinimumLimitValidator:
    def __init__(self, des):
        self.des = des

    def __call__(self, value, *args, **kwargs):
        minimum = int(get_config_from_model(f'min_{self.des}'))
        if minimum > value:
            raise ValidationError(f"{value} is below minimum {minimum} limit of {self.des}")


class MinMaxLimitValidator:
    def __init__(self, des):
        self.des = des

    def __call__(self, value, *args, **kwargs):
        minimum = int(get_config_from_model(f'min_{self.des}'))
        maximum = int(get_config_from_model(f'max_{self.des}'))
        if value > maximum:
            raise ValidationError(f"{value} exceed maximum {maximum} limit of {self.des}")
        if minimum > value:
            raise ValidationError(f"{value} is below minimum {minimum} limit of {self.des}")
