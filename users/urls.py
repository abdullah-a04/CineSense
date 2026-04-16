from django.contrib import admin
from django.urls import path, include
from users import views # Import your app's views
from . import views

urlpatterns = [
    path('register/', views.register, name='register'), # THE FIX IS HERE
    path('survey/', views.preference_survey, name='preference_survey'),
    path('home/', views.home, name='home'),

    path('add-to-watchlist/<int:movie_id>/', views.add_to_watchlist, name='add_to_watchlist'),
    path('rate-movie/<int:movie_id>/', views.rate_movie, name='rate_movie'),

    path('my-list/', views.my_list, name='my_list'),
    path('remove-from-watchlist/<int:movie_id>/', views.remove_from_watchlist, name='remove_from_watchlist'),
    path('delete-rating/<int:movie_id>/', views.delete_rating, name='delete_rating'),

    path('search/', views.search, name='search'),
]