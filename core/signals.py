from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile, Role

User = get_user_model()

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if not created:
        return
    role = Role.ADMIN if instance.is_superuser else Role.INSPECTOR
    Profile.objects.get_or_create(user=instance, defaults={"role": role})
