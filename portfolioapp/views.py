import requests
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.shortcuts import render


def about(request):
    return render(request, 'about.html')


def resume(request):
    return render(request, 'resume.html')


def portfolio(request):
    return render(request, 'portfolio.html')


def contact(request):
    recaptcha_site_key = settings.GOOGLE_RECAPTCHA_SITE_KEY
    recaptcha_secret_key = settings.GOOGLE_RECAPTCHA_SECRET_KEY

    if request.method == 'POST':
        name = request.POST.get('fullname')
        email = request.POST.get('email')
        message = request.POST.get('message')
        recaptcha_response = request.POST.get('g-recaptcha-response')

        if not name or not email or not message or not recaptcha_response:
            return render(request, 'contact.html', {
                'error': 'All fields are required.',
                'recaptcha_site_key': recaptcha_site_key
            })

        recaptcha_verify_url = 'https://recaptchaenterprise.googleapis.com/v1/projects/shae-kuhnke-1744126552098/assessments?key=API_KEY'
        recaptcha_data = {
            'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response
        }
        recaptcha_result = requests.post(recaptcha_verify_url, data=recaptcha_data)
        recaptcha_result_json = recaptcha_result.json()

        if not recaptcha_result_json['success']:
            return render(request, 'contact.html', {
                'error': 'reCAPTCHA validation failed. Please try again.',
                'recaptcha_site_key': recaptcha_site_key
            })

        email_subject = 'New Contact Submission'
        email_body = render_to_string('contact_email.txt', {
            'name': name,
            'email': email,
            'message': message,
        })

        email_message = EmailMessage(
            email_subject,
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            ['shaejk29@gmail.com']
        )

        try:
            print('success')
            email_message.send()
            return render(request, 'contact.html', {
                'success': 'Thank you for reaching out! I will get back to you shortly!',
                'recaptcha_site_key': recaptcha_site_key
            })
        except Exception as e:
            return render(request, 'contact.html', {
                'error': f'An error occurred: {str(e)}',
                'recaptcha_site_key': recaptcha_site_key
            })

    return render(request, 'contact.html', {
        'recaptcha_site_key': recaptcha_site_key
    })


def custom_404(request, exception):
    return render(request, '404.html', {}, status=404)
