from django.conf import settings


def s3_assets_url(request):
    return {'S3_ASSETS_URL': settings.S3_ASSETS_URL}
