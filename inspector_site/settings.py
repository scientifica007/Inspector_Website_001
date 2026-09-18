import os
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.getenv("DJANGO_SECRET_KEY","dev-only-change-me")
DEBUG=os.getenv("DJANGO_DEBUG","1")=="1"
ALLOWED_HOSTS=[x.strip() for x in os.getenv("DJANGO_ALLOWED_HOSTS","localhost,127.0.0.1,testserver").split(",") if x.strip()]
INSTALLED_APPS=["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","core"]
MIDDLEWARE=["django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF="inspector_site.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","core.context_processors.access_flags"]}}]
WSGI_APPLICATION="inspector_site.wsgi.application"
if os.getenv("POSTGRES_DB"):
    DATABASES={"default":{"ENGINE":"django.db.backends.postgresql","NAME":os.environ["POSTGRES_DB"],"USER":os.environ["POSTGRES_USER"],"PASSWORD":os.environ["POSTGRES_PASSWORD"],"HOST":os.getenv("POSTGRES_HOST","127.0.0.1"),"PORT":os.getenv("POSTGRES_PORT","5432")}}
else:
    DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS=[
{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},
{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},
{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE="ar"
TIME_ZONE="Africa/Algiers"
USE_I18N=True
USE_TZ=True
STATIC_URL="static/"
STATICFILES_DIRS=[BASE_DIR/"static"]
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="login"
LOGIN_REDIRECT_URL="dashboard"
LOGOUT_REDIRECT_URL="login"
SESSION_COOKIE_SECURE=os.getenv("DJANGO_SECURE_COOKIES","0")=="1"
CSRF_COOKIE_SECURE=SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT=os.getenv("DJANGO_SECURE_SSL_REDIRECT","0")=="1"
