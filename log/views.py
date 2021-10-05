from log.models import Logging

PERFORMANCE = True


def debug_function(description="", *args, **kwargs):
    def inner(func):
        if not PERFORMANCE:
            try:
                func(*args)
            except Exception as e:
                exception_log(e, description)
                raise e
        else:
            func(*args)

    return inner


def exception_log(e: Exception, description="Nothing"):
    Logging.objects.create(error_type=str(type(e).__name__), error_message=str(e), description=description)


def data_error_log(error_type='Wrong Data', description="Nothing"):
    Logging.objects.create(error_type=error_type, error_message=description, description=description)
