from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

def role_required(role):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if getattr(request.user, "role", None) != role:
                return HttpResponseForbidden("Forbidden: wrong role")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
