from .models import Role

def access_flags(request):
    user = getattr(request, "user", None)
    admin_access = False
    if user and user.is_authenticated:
        profile = getattr(user, "profile", None)
        admin_access = bool(user.is_superuser or (profile and profile.role == Role.ADMIN))
    return {"admin_access": admin_access}
