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

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        recaptcha_response = request.POST.get('g-recaptcha-response')

        if not name or not email or not message:
            return render(request, 'contact.html', {
                'error': 'All fields are required.',
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
            ['shaekuhnke@gmail.com']
        )

        try:
            email_message.send()
            return render(request, 'contact.html', {
                'success': 'Thank you for your message. We will get back to you shortly.',
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
