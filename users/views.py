from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from engine_logic import get_recommendations, get_hybrid_recommendations, search_movies_by_title
import requests
from django.http import HttpResponseRedirect
import random


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
        directors_list = request.POST.getlist('directors')
        profile.favorite_directors = " ".join(directors_list)

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
    # GET request - render the blank form
    genres_list = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Romance', 'Thriller', 'Animation', 'Fantasy', 'Crime', 'Mystery', 'Adventure', 'Family']
    
    # 1. Create a Master Pool of diverse directors
    MASTER_DIRECTORS = [
        {'id': 'nolan', 'name': 'Christopher Nolan', 'value': 'ChristopherNolan', 'movie': 'The Dark Knight'},
        {'id': 'villeneuve', 'name': 'Denis Villeneuve', 'value': 'DenisVilleneuve', 'movie': 'Dune'},
        {'id': 'gerwig', 'name': 'Greta Gerwig', 'value': 'GretaGerwig', 'movie': 'Barbie'},
        {'id': 'tarantino', 'name': 'Quentin Tarantino', 'value': 'QuentinTarantino', 'movie': 'Django Unchained'},
        {'id': 'bong', 'name': 'Bong Joon-ho', 'value': 'BongJoonho', 'movie': 'Parasite'},
        {'id': 'jackson', 'name': 'Peter Jackson', 'value': 'PeterJackson', 'movie': 'Lord of the Rings'},
        {'id': 'peele', 'name': 'Jordan Peele', 'value': 'JordanPeele', 'movie': 'Get Out'},
        {'id': 'fincher', 'name': 'David Fincher', 'value': 'DavidFincher', 'movie': 'Gone Girl'},
        {'id': 'deltoro', 'name': 'Guillermo del Toro', 'value': 'GuillermoDelToro', 'movie': "Pan's Labyrinth"},
        {'id': 'miyazaki', 'name': 'Hayao Miyazaki', 'value': 'HayaoMiyazaki', 'movie': 'Spirited Away'},
        {'id': 'king', 'name': 'Paul King', 'value': 'PaulKing', 'movie': 'Paddington'},
        {'id': 'spielberg', 'name': 'Steven Spielberg', 'value': 'StevenSpielberg', 'movie': 'Jurassic Park'},
        {'id': 'scorsese', 'name': 'Martin Scorsese', 'value': 'MartinScorsese', 'movie': 'Goodfellas'},
        {'id': 'wright', 'name': 'Edgar Wright', 'value': 'EdgarWright', 'movie': 'Baby Driver'},
        {'id': 'coppola', 'name': 'Sofia Coppola', 'value': 'SofiaCoppola', 'movie': 'Lost in Translation'},
        {'id': 'wes', 'name': 'Wes Anderson', 'value': 'WesAnderson', 'movie': 'The Grand Budapest Hotel'},
    ]
    
    # 2. Randomly select 8 from the pool
    random_directors = random.sample(MASTER_DIRECTORS, 8)
    
    return render(request, 'users/survey.html', {
        'genres': genres_list,
        'directors': random_directors # Pass the 8 random directors to the HTML
    })

@login_required
def home(request):
    profile = request.user.profile
    
    if not profile.survey_completed:
        return redirect('preference_survey')
        
    # --- 1. THE "HARD" QUERY ---
    hard_query_parts = [
        profile.favorite_genres,
        profile.preferred_era,
        profile.favorite_actors,
        profile.favorite_directors,
        profile.favorite_movie
    ]
    hard_query = " ".join([q for q in hard_query_parts if q])
    
    # --- 2. THE "SOFT" QUERY ---
    soft_query_parts = [
        profile.favorite_genres,
        profile.preferred_era
    ]
    soft_query = " ".join([q for q in soft_query_parts if q])
    
    # --- RUN THE AI ENGINE TWICE ---
    hard_df = get_hybrid_recommendations(request.user, hard_query)
    soft_df = get_hybrid_recommendations(request.user, soft_query)
    
    all_hard = hard_df.to_dict('records')
    all_soft = soft_df.to_dict('records')
    
    # --- 🎲 1. THE STOCHASTIC HARD MATCHES (10 Movies) ---
    # Increased the pool to 30 so there is still plenty of room to shuffle
    hard_pool = all_hard[:30]
    
    # Now sampling 10 movies
    if len(hard_pool) >= 10:
        top_matches = random.sample(hard_pool, 10)
    else:
        top_matches = hard_pool
        
    shown_movie_ids = [movie['id'] for movie in top_matches]
    
    # --- 🎲 2. THE STOCHASTIC SOFT MATCHES (10 Movies) ---
    # Increased the soft pool to 50 remaining movies
    soft_pool = [m for m in all_soft if m['id'] not in shown_movie_ids][:50]
    
    if len(soft_pool) >= 10:
        soft_matches = random.sample(soft_pool, 10)
    else:
        soft_matches = soft_pool
        # Update the math to calculate how many we need to reach 10
        needed = 10 - len(soft_matches)
        more_hard = [m for m in all_hard if m['id'] not in shown_movie_ids]
        soft_matches.extend(more_hard[:needed])
        
    # Absolute Emergency Fallback
    if len(soft_matches) == 0:
        soft_matches = all_hard[:10]
        
    context = {
        'top_matches': top_matches,
        'soft_matches': soft_matches,
        'profile': profile,
    }
    
    return render(request, 'users/home.html', context)

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
            
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))

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
            
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/home/'))

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