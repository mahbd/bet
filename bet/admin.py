from django.contrib.admin import AdminSite as MainAdminSite, ModelAdmin as MainModelAdmin


class ModelAdmin(MainModelAdmin):
    pass


class AdminSite(MainAdminSite):
    pass

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
