from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from engine_logic import get_recommendations
from .models import Profile

@login_required
def preference_survey(request):
    if request.method == 'POST':
        # Capture data from the frontend form
        selected_genres = request.POST.getlist('genres')
        favorite_stars = request.POST.get('stars', '')

        # Get the current user's profile
        profile = request.user.profile
        
        # Save the data to the profile
        profile.favorite_genres = ",".join(selected_genres)
        profile.favorite_actors = favorite_stars
        profile.survey_completed = True
        profile.save()

        # Redirect to the home page after saving the survey data
        return redirect('home')

    # List of genres to display as options on the page
    genres_list = [
        'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 
        'Drama', 'Family', 'Fantasy', 'Horror', 'Mystery', 
        'Romance', 'Sci-Fi', 'Thriller'
    ]
    
    return render(request, 'users/survey.html', {'genres': genres_list})
def home(request):
    user_profile = request.user.profile
    # Combine genres and actors into a single search string
    user_query = f"{user_profile.favorite_genres} {user_profile.favorite_actors}"
    
    # Get recommendations and convert to a list of dictionaries for the HTML
    recommendations_df = get_recommendations(user_query)
    recommendations = recommendations_df.to_dict('records')
    
    return render(request, 'users/home.html', {'movies': recommendations})