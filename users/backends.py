import json
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
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
    if request.headers.get('x-auth-token', False):
        jwt_str = request.headers['x-auth-token']
        if not jwt_str:
            return None
        try:
            st = jwt.JWT(key=jwk_key(), jwt=jwt_str)
            data = json.loads(st.claims)
            password = data.get("password", "none")
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
