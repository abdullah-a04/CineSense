from django.urls import path
from . import views

urlpatterns = [
    path('survey/', views.preference_survey, name='preference_survey'),
    path('home/', views.home, name='home'),
]