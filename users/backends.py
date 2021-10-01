import json
from functools import wraps
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model, REDIRECT_FIELD_NAME
from django.contrib.auth.backends import ModelBackend
from django.shortcuts import resolve_url
from jwcrypto import jwt, jws, jwk
from rest_framework.authentication import TokenAuthentication

from bet.settings import JWK_KEY
from users.models import Club

UserModel = get_user_model()


def jwk_key():
    return jwk.JWK(**json.loads(JWK_KEY))


def jwt_writer(**kwargs):
    key = jwk_key()
    token = jwt.JWT(header={'alg': 'HS256'}, claims=kwargs)
    token.make_signed_token(key)
    return token.serialize()


def validate_jwt(jwt_str):
    if not jwt_str:
        return None
    try:
        st = jwt.JWT(key=jwk_key(), jwt=jwt_str)
        data = json.loads(st.claims)
        login_key = data.get("login_key", "none")
        try:
            return UserModel.objects.get(username=data.get('username'), email=data.get('email'),
                                         login_key=login_key)
        except UserModel.DoesNotExist:
            return None
    except (jws.InvalidJWSSignature, jws.InvalidJWSObject, ValueError):
        return None


def get_current_club(request):
    if request.headers.get('club-token', False):
        jwt_str = request.headers['club-token']
        if not jwt_str:
            return None
        try:
            st = jwt.JWT(key=jwk_key(), jwt=jwt_str)
            data = json.loads(st.claims)
            password = data.get("key", "none")
            club_id = data.get("id", "none")
            clubs = Club.objects.filter(id=club_id)
            if clubs:
                club = clubs.first()
                if club.password == password:
                    return club
            return None
        except (jws.InvalidJWSSignature, jws.InvalidJWSObject, ValueError):
            return None


def is_valid_jwt_header(request):
    if request.headers.get('x-auth-token', False):
        jwt_str = request.headers['x-auth-token']
        return validate_jwt(jwt_str)
    if request.headers.get('AUTH_TOKEN', False):
        jwt_str = request.headers['AUTH_TOKEN']
        return validate_jwt(jwt_str)


class RestBackendWithJWT(TokenAuthentication):
    def authenticate(self, request):
        user = is_valid_jwt_header(request)
        return user, None


class ModelBackendWithJWT(ModelBackend):
    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        if request.headers.get('x-auth-token', False):
            user = is_valid_jwt_header(request)
            if user:
                return user
        if (username is None and email is None) or password is None:
            return
        try:
            if email:
                user = UserModel.objects.get(email=email)
            else:
                user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user


def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                path, resolved_login_url, redirect_field_name)
        return _wrapped_view
    return decorator


def superuser_only(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
