from pathlib import Path
from os import getenv


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-hqkj0wxp3ims=qr)o$vvd=$qpbhei%1wf^gpa0cuz_^xghjh-a'

TRANSITLAND_API_KEY = getenv('TRANSITLAND_API_KEY')
GTFS_REALTIME_PROTO_URL = getenv('GTFS_REALTIME_PROTO_URL')
ORS_HOST = getenv('ORS_HOST')
ORS_PORT = getenv('ORS_PORT')

NEXTBIKE_API_URL = getenv('NEXTBIKE_API_URL')

DOTT_SCOOTERS_API_URL = getenv('DOTT_SCOOTERS_API_URL')
BOLT_SCOOTERS_API_URL = getenv('BOLT_SCOOTERS_API_URL')
BOLT_DEVICE_ID = getenv('BOLT_DEVICE_ID')
BOLT_PHONE_NUMBER = getenv('BOLT_PHONE_NUMBER')

ALLOWED_CARRIERS = ['WKD', 'ZTM', 'KM']

ONESTOP_IDS = {
    carrier: getenv(f'{carrier}_ONESTOP_ID')
    for carrier in ALLOWED_CARRIERS
}
ONESTOP_IDS.update({
    'ZTM_RT_V': getenv('ZTM_RT_VEHICLES_ONESTOP_ID'),
    'ZTM_RT_A': getenv('ZTM_RT_ALERTS_ONESTOP_ID'),
    'WKD_RT_V': getenv('WKD_RT_ONESTOP_ID'),
})

SERVED_FEEDS = list(ONESTOP_IDS.keys())

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_celery_beat',
    'django_celery_results',
    'rest_framework',
    'Tasker',
    'Stops',
    'Routes',
    'Bikes',
]

MIDDLEWARE = [
    #'Stops.middleware.ProcessExceptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': getenv('DB_NAME'),
        'USER': getenv('DB_USER'),
        'PASSWORD': getenv('DB_PASSWORD'),
        'HOST': getenv('DB_HOST', 'localhost'),
        'PORT': getenv('DB_PORT', '5432'),
    }
}

MONGO_URI = getenv('MONGO_URI')
MONGO_DB_NAME = getenv('MONGO_DB_NAME')

REDIS_HOST = getenv('REDIS_HOST')
REDIS_PORT = getenv('REDIS_PORT')
REDIS = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'

CELERY_BROKER_URL = REDIS
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Warsaw'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'


LOGS_DIR = BASE_DIR / 'logs'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '[{asctime}] [{levelname}] [{name}] [{funcName}:{lineno}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
        },
        'file_all': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'app.log',
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        },
        'file_celery': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'celery.log',
            'maxBytes': 10*1024*1024,
            'backupCount': 3,
            'formatter': 'detailed',
            'encoding': 'utf-8',
        }
    },
    'loggers': {
        'celery.worker': {
            'handlers': ['console', 'file_celery'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.beat': {
            'handlers': ['console', 'file_celery'],
            'level': 'INFO',
            'propagate': False,
        },
        'Tasker': {
            'handlers': ['console', 'file_celery'],
            'level': 'INFO',
            'propagate': False,
        },
        'Tasker.services.tasks.gtfs': {
            'handlers': ['file_celery'],
            'level': 'INFO',
            'propagate': False,
        },
        'Tasker.services.tasks.bikes': {
            'handlers': ['file_celery'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}