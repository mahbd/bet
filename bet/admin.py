from django.contrib.admin import AdminSite as MainAdminSite, ModelAdmin as MainModelAdmin
from django.shortcuts import render
from django.urls import path

from betting.models import TYPE_DEPOSIT, TYPE_WITHDRAW, METHOD_TRANSFER
from betting.views import unverified_transaction_count, active_matches, \
    active_bet_scopes_count, generate_admin_dashboard_data


class ModelAdmin(MainModelAdmin):
    pass


class AdminSite(MainAdminSite):
    def each_context(self, request):
        contexts = super().each_context(request)
        contexts['developer_name'] = 'Mahmudul Alam'
        contexts['unverified_deposit'] = unverified_transaction_count(t_type=TYPE_DEPOSIT)
        contexts['unverified_withdraw'] = unverified_transaction_count(t_type=TYPE_WITHDRAW)
        contexts['unverified_transfer'] = unverified_transaction_count(t_type=TYPE_WITHDRAW, method=METHOD_TRANSFER)
        contexts['active_matches'] = active_matches().count()
        contexts['active_bet_scopes'] = active_bet_scopes_count()
        return contexts

    def home(self, request):
        request.current_app = self.name
        context = dict(
            self.each_context(request),
            data=generate_admin_dashboard_data(),
        )

        return render(request, 'admin/home.html', context)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('home/', self.home, name='home')
        ]
        return my_urls + urls


site = AdminSite('admin')
default_site = site


def register(*models, site=None):
    from django.contrib.admin import ModelAdmin

    def _model_admin_wrapper(admin_class):
        if not models:
            raise ValueError('At least one model must be passed to register.')

        admin_site = site or default_site

        if not isinstance(admin_site, AdminSite):
            raise ValueError('site must subclass AdminSite')

        if not issubclass(admin_class, ModelAdmin):
            raise ValueError('Wrapped class must subclass ModelAdmin.')

        admin_site.register(models, admin_class=admin_class)

        return admin_class

    return _model_admin_wrapper


def display(function=None, *, boolean=None, ordering=None, description=None, empty_value=None):
    def decorator(func):
        if boolean is not None and empty_value is not None:
            raise ValueError(
                'The boolean and empty_value arguments to the @display '
                'decorator are mutually exclusive.'
            )
        if boolean is not None:
            func.boolean = boolean
        if ordering is not None:
            func.admin_order_field = ordering
        if description is not None:
            func.short_description = description
        if empty_value is not None:
            func.empty_value_display = empty_value
        return func

    if function is None:
        return decorator
    else:
        return decorator(function)
