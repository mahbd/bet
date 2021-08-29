from django.shortcuts import render

from log.models import Logging


def custom_log(e: Exception, description="Nothing"):
    Logging.objects.create(error_type=str(type(e).__name__), error_message=str(e), description=description)
