from django.contrib.auth import login

from .models import User


def login_user(request):
    try:
        client_data = json.loads(request.body)
    except json.JSONDecodeError:
        post = dict(request.POST)
        if post.get('username') or post.get('email') or post.get('idToken'):
            client_data = {
                'email': post.get('email')[0] if type(post.get('email')) == list else post.get('email'),
                'username': post.get('username')[0] if type(post.get('username')) == list else post.get('username'),
                'password': post.get('password')[0] if type(post.get('password')) == list else post.get('password'),
                'idToken': post.get('idToken')[0] if type(post.get('idToken')) == list else post.get('idToken'),
            }
        else:
            return JsonResponse({"errors": "No data provided"}, status=400)
    user = login_user_local(request, client_data)
    if not user:
        return JsonResponse({"errors": "Couldn't login"}, status=400)
    jwt_str = serialize_user(user)
    return JsonResponse({"jwt": jwt_str})
