from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("health/", views.health, name="health"),
    path("institutions/", views.institution_list, name="institution_list"),
    path("institutions/new/", views.institution_create, name="institution_create"),
    path("inspections/new/", views.inspection_create, name="inspection_create"),
]
