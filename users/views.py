from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from engine_logic import get_recommendations, get_hybrid_recommendations, search_movies_by_title
import requests

from engine_logic import get_recommendations, get_hybrid_recommendations
from .models import Profile, Watchlist, Rating

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately after they register
            login(request, user)
            # Send them to the dashboard (which will instantly redirect them to the survey!)
            return redirect('home')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

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

        return redirect('home')

    # List of genres to display as options on the page
    genres_list = [
        'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 
        'Drama', 'Family', 'Fantasy', 'Horror', 'Mystery', 
        'Romance', 'Sci-Fi', 'Thriller'
    ]
    
    return render(request, 'users/survey.html', {'genres': genres_list})


@login_required 
def home(request):
    user_profile = request.user.profile
    
    if not user_profile.survey_completed:
        return redirect('preference_survey')

    user_query = f"{user_profile.favorite_genres} {user_profile.favorite_actors}"
    
    # THE UPGRADE: We now pass the 'request.user' AND the 'user_query' into the Hybrid Engine!
    recommendations_df = get_hybrid_recommendations(request.user, user_query)
    recommendations = recommendations_df.to_dict('records')
    
    return render(request, 'users/home.html', {'movies': recommendations})

@login_required
def add_to_watchlist(request, movie_id):
    if request.method == 'POST':
        movie_title = request.POST.get('movie_title')
        
        # Check if it already exists to prevent database crash (integrity error)
        if not Watchlist.objects.filter(user=request.user, movie_id=movie_id).exists():
            Watchlist.objects.create(user=request.user, movie_id=movie_id, movie_title=movie_title)
            messages.success(request, f"🍿 '{movie_title}' added to your watchlist!")
        else:
            messages.info(request, f"'{movie_title}' is already in your watchlist.")
            
    return redirect('home')

@login_required
def rate_movie(request, movie_id):
    if request.method == 'POST':
        movie_title = request.POST.get('movie_title')
        score = request.POST.get('score')
        
        # update_or_create is a brilliant Django shortcut. If they haven't rated it, 
        # it creates it. If they have, it updates their old score!
        rating, created = Rating.objects.update_or_create(
            user=request.user, 
            movie_id=movie_id,
            defaults={'movie_title': movie_title, 'score': score}
        )
        
        if created:
            messages.success(request, f"⭐ You rated '{movie_title}' {score} stars!")
        else:
            messages.success(request, f"🔄 Your rating for '{movie_title}' was updated to {score} stars!")
            
    return redirect('home')

@login_required
def my_list(request):
    # Fetch the user's watchlist, ordered by newest first
    user_watchlist = Watchlist.objects.filter(user=request.user).order_by('-added_at')
    
    # Fetch the user's ratings, ordered by newest first
    user_ratings = Rating.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'watchlist': user_watchlist,
        'ratings': user_ratings
    }
    
    return render(request, 'users/my_list.html', context)

@login_required
def remove_from_watchlist(request, movie_id):
    if request.method == 'POST':
        # Find the specific entry for this user and delete it
        deleted, _ = Watchlist.objects.filter(user=request.user, movie_id=movie_id).delete()
        if deleted:
            messages.success(request, "🗑️ Movie removed from your watchlist.")
    return redirect('my_list')

@login_required
def delete_rating(request, movie_id):
    if request.method == 'POST':
        # Find the specific rating and delete it
        deleted, _ = Rating.objects.filter(user=request.user, movie_id=movie_id).delete()
        if deleted:
            messages.success(request, "🗑️ Rating permanently deleted.")
    return redirect('my_list')

import requests # <--- IMPORTANT: Add this at the very top of views.py

@login_required
def search(request):
    query = request.GET.get('q', '')
    tmdb_results = []
    
    if query:
        # Use your active TMDB API Key
        api_key = 'dec1382fbb89751f2f231fee7ec947e5'
        
        # We call the TMDB Search API directly
        url = "https://api.themoviedb.org/3/search/movie"
        params = {
            'api_key': api_key,
            'query': query,
            'language': 'en-US',
            'page': 1,
            'include_adult': 'false'
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                tmdb_results = data.get('results', [])[:20] # Grab top 20 live results
                
                # Debugging: This will print results to your terminal so you can see if it worked
                print(f"DEBUG: Found {len(tmdb_results)} results for {query}")
        except Exception as e:
            print(f"DEBUG ERROR: {e}")
            
    # IMPORTANT: We send 'tmdb_results' to the template as 'movies'
    return render(request, 'users/search_results.html', {
        'movies': tmdb_results, 
        'query': query
    })