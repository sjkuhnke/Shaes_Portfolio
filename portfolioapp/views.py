import json
import os
import re
from pathlib import Path

import markdown
import requests
from django.core.mail import EmailMessage
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.shortcuts import render
from django.utils.safestring import mark_safe
from markdown.extensions.nl2br import Nl2BrExtension


def about(request):
    json_path = os.path.join(settings.BASE_DIR, 'portfolioapp/static', 'data', 'testimonials.json')
    with open(json_path, 'r', encoding='utf-8') as file:
        testimonials = json.load(file)

    return render(request, 'about.html', {'testimonials': testimonials})


def resume(request):
    return render(request, 'resume.html')


def portfolio(request):
    json_path = os.path.join(settings.BASE_DIR, 'portfolioapp/static', 'data', 'projects.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    return render(request, 'portfolio.html', {'projects': projects})


def project(request, pk):
    json_path = os.path.join(settings.BASE_DIR, 'portfolioapp/static', 'data', 'projects.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        projects = json.load(f)
    proj = next((p for p in projects if p['id'] == int(pk)), None)
    if not proj:
        raise Http404("Project not found")
    return render(request, 'project.html', {'project': proj})


def contact(request):
    recaptcha_site_key = settings.GOOGLE_RECAPTCHA_SITE_KEY
    recaptcha_secret_key = settings.GOOGLE_RECAPTCHA_SECRET_KEY

    if request.method == 'POST':
        name = request.POST.get('fullname')
        email = request.POST.get('email')
        company = request.POST.get('company')
        message = request.POST.get('message')
        recaptcha_response = request.POST.get('g-recaptcha-response')

        if not name or not email or not message or not recaptcha_response:
            return render(request, 'contact.html', {
                'error': 'All fields are required.',
                'recaptcha_site_key': recaptcha_site_key
            })

        recaptcha_verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        recaptcha_data = {
            'secret': recaptcha_secret_key,
            'response': recaptcha_response
        }
        recaptcha_result = requests.post(recaptcha_verify_url, data=recaptcha_data)
        recaptcha_result_json = recaptcha_result.json()

        recaptcha_score = recaptcha_result_json.get('score', 0)

        if not recaptcha_result_json.get('success') or recaptcha_score < 0.5:
            return render(request, 'contact.html', {
                'error': 'reCAPTCHA verification failed. Please try again.',
                'recaptcha_site_key': recaptcha_site_key
            })

        email_subject = 'New Contact Submission'
        email_body = render_to_string('contact_email.txt', {
            'name': name,
            'email': email,
            'company': company,
            'message': message,
        })

        email_message = EmailMessage(
            email_subject,
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            ['shaejk29@gmail.com']
        )

        try:
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


def xhenos(request):
    """Main download page for Pokemon Xhenos"""
    versions_path = os.path.join(settings.BASE_DIR, 'content', 'versions', 'versions.json')
    with open(versions_path, 'r', encoding='utf-8') as f:
        version_data = json.load(f)

    latest = version_data['latest'].copy()
    latest.update({
        'download_windows': latest['downloads']['windows'],
        'download_mac': latest['downloads']['mac'],
        'download_jar': latest['downloads']['jar'],
    })

    previous_versions = []
    for version in version_data.get('previous', []):
        version_copy = version.copy()
        version_copy.update({
            'download_windows': version['downloads']['windows'],
            'download_mac': version['downloads']['mac'],
            'download_jar': version['downloads']['jar'],
        })
        previous_versions.append(version_copy)

    context = {
        "latest": latest,
        "previous_versions": previous_versions,
        "categories": {title: icon for title, icon in CATEGORY_ICONS.items()}
    }

    return render(request, "xhenos_downloads.html", context)


def changelog_page(request, version):
    """Full view for changelog"""
    try:
        changelog_html, toc_html = read_changelog(version)
        if changelog_html:
            context = {
                'content': mark_safe(changelog_html),
                'toc': mark_safe(toc_html) if toc_html else None,
                'title': f'Changelog - Pokémon Xhenos v{version}',
                'back_url': '/xhenos/',
                'back_text': 'Back to Downloads'
            }
            return render(request, 'markdown_page.html', context)
        else:
            raise Http404("Changelog not found")
    except Exception as e:
        print(e)
        raise Http404("Error loading changelog")


CATEGORY_ICONS = {
    "New Features": '<i class="fa-solid fa-star"></i>',
    "Feature Updates": '<i class="fa-solid fa-wrench"></i>',
    "Bug Fixes": '<i class="fa-solid fa-bug"></i>',
    "Move Changes": '<i class="fa-solid fa-bolt"></i>',
    "Pokemon Changes": '<i class="fa-solid fa-dragon"></i>',
    "Trainer Changes": '<i class="fa-solid fa-user"></i>',
}


def ai_guide(request):
    """Serve the AI trainer guide"""
    try:
        guide_path = os.path.join(settings.BASE_DIR, 'content', 'guides', 'comprehensive_trainer_ai_guide.md')

        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()

        html, toc_html = process_markdown_content(content)

        context = {
            'content': mark_safe(html),
            'toc': mark_safe(toc_html) if toc_html else None,
            'title': 'Trainer AI Guide - Pokémon Xhenos',
            'back_url': '/xhenos/',
            'back_text': 'Back to Downloads'
        }

        return render(request, 'markdown_page.html', context)

    except FileNotFoundError:
        raise Http404("No AI guide found")
    except Exception as e:
        print(e)
        raise Http404("Error loading AI Guide")


def process_markdown_content(content):
    """Process markdown content with consistent configuration for both changelogs and guides"""
    md = markdown.Markdown(
        extensions=[
            'extra',
            'toc',
            'codehilite',
            'fenced_code',
            'tables',
            'sane_lists'
        ],
        extension_configs={
            'toc': {
                'permalink': False,
                'baselevel': 1,
                'toc_depth': 2,
                'slugify': lambda value, separator: re.sub(r'[-\s]+', separator, re.sub(r'[^\w\s-]', '', value).strip().lower()),
            },
            'codehilite': {
                'css_class': 'codehilite',
                'use_pygments': False,
                'noclasses': True
            }
        },
        output_format='html'
    )

    html = md.convert(content)
    toc_html = md.toc if hasattr(md, 'toc') and md.toc.strip() else None

    if toc_html:
        # Remove the entire H1 <li> element (opening tag, link, and nested ul opening)
        # This leaves us with: <div class="toc"><ul><ul>...H2 items...</ul></li></ul></div>
        toc_html = re.sub(
            r'(<div class="toc">\s*<ul>\s*)<li><a[^>]*>[^<]*</a>\s*<ul>',
            r'\1<ul>',  # Keep one <ul> tag
            toc_html,
            count=1,
            flags=re.DOTALL
        )

        # Now remove the trailing </li></ul> that belonged to the H1, leaving just </ul></div>
        toc_html = re.sub(
            r'</ul>\s*</li>\s*</ul>(\s*</div>)$',
            r'</ul>\1',
            toc_html,
            count=1,
            flags=re.DOTALL
        )

    return html, toc_html


def read_changelog(version):
    """Read and process changelog for a specified version"""
    path = Path(f"content/changelogs/changelog_{version}.md")
    if not path.exists():
        return None, None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Convert Markdown to HTML
    html, toc_html = process_markdown_content(content)

    # Insert icons into <h2> headings
    for category, icon_html in CATEGORY_ICONS.items():
        pattern = rf"<h2([^>]*)>(\s*){re.escape(category)}(\s*)</h2>"
        replacement = rf'<h2\1>{icon_html} {category}</h2>'
        html = re.sub(pattern, replacement, html)

    return html, toc_html


def custom_404(request, exception):
    return render(request, '404.html', {}, status=404)
