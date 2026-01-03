"""
URL configuration for shaes_portfolio project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from portfolioapp import views

urlpatterns = [
    path('', views.about, name='about'),
    path('resume/', views.resume, name='resume'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('contact/', views.contact, name='contact'),
    path('portfolio/<int:pk>/', views.project, name='project'),
    path('xhenos/', views.xhenos, name='xhenos'),
    path('xhenos/changelog/<str:version>/', views.changelog_page, name='changelog_page'),
    path('xhenos/ai-guide/', views.ai_guide, name='ai_guide'),
    path('xhenos/trainers/', views.trainer_database, name='trainer_database'),
    path('xhenos/trainers/autocomplete/', views.trainer_autocomplete, name='trainer_autocomplete'),
    path('xhenos/trainers/<trainer_name>/', views.trainer_lookup, name='trainer_lookup'),
    path('xhenos/players/<str:player_name>/', views.player_lookup, name='player_lookup'),
    path('xhenos/upload-battle/', views.upload_battle_history, name='upload_battle_history'),
]
