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
        profile = request.user.profile
        
        # 1. Catch all the data from the new HTML form
        genres = request.POST.get('genres', '')
        era = request.POST.get('era', '')
        
        actor1 = request.POST.get('actor1', '').replace(" ", "")
        actor2 = request.POST.get('actor2', '').replace(" ", "")
        actor3 = request.POST.get('actor3', '').replace(" ", "")
        actor4 = request.POST.get('actor4', '').replace(" ", "")
        actor5 = request.POST.get('actor5', '').replace(" ", "")
        actors_list = [a for a in [actor1, actor2, actor3, actor4, actor5] if a]
        
        # Directors (Combine the 2 text boxes)
        director1 = request.POST.get('director1', '').replace(" ", "")
        director2 = request.POST.get('director2', '').replace(" ", "")
        director3 = request.POST.get('director3', '').replace(" ", "")
        directors_list = [d for d in [director1, director2, director3] if d]

        # MOVIES (Now catches 3 - Note: We do NOT remove spaces for movie titles)
        movie1 = request.POST.get('movie1', '')
        movie2 = request.POST.get('movie2', '')
        movie3 = request.POST.get('movie3', '')
        movies_list = [m for m in [movie1, movie2, movie3] if m]
        
        # 2. Save it all safely to the Database Profile
        profile.favorite_genres = genres
        profile.preferred_era = era
        profile.favorite_actors = " ".join(actors_list) # We join them with a space to match the "soup" format in engine_logic.py
        profile.favorite_directors = " ".join(directors_list)
        profile.favorite_movie = " ".join(movies_list)
        
        profile.survey_completed = True
        profile.save()
        
        messages.success(request, "Profile built successfully! Analyzing your cinematic DNA...")
        return redirect('home')

    # GET request - render the blank form
    genres_list = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Romance', 'Thriller', 'Animation', 'Fantasy', 'Crime', 'Mystery', 'Adventure']
    return render(request, 'users/survey.html', {'genres': genres_list})

@login_required
def home(request):
    profile = request.user.profile
    
    # Check if they need to take the survey
    if not profile.survey_completed:
        return redirect('preference_survey')
        
    # BUILD THE MEGA QUERY: Combine all their preferences into one massive string
    query_parts = [
        profile.favorite_genres,
        profile.preferred_era,
        profile.favorite_actors,
        profile.favorite_directors,
        profile.favorite_movie
    ]
    # Filter out any blank answers and join them with a space
    mega_query = " ".join([q for q in query_parts if q])
    
    # Feed the massive string to your AI Engine
    recommended_df = get_hybrid_recommendations(request.user, mega_query)
    
    # Convert DataFrame to dictionary for the HTML template
    movies = recommended_df.to_dict('records')
    
    return render(request, 'users/home.html', {'movies': movies})

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