import pandas as pd
import numpy as np
from ast import literal_eval
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- PHASE 1: DATA LOADING & PREPROCESSING ---

df_movies = pd.read_csv('tmdb_5000_movies.csv')
df_credits = pd.read_csv('tmdb_5000_credits.csv')

# Merge on Movie ID
df_credits.columns = ['id', 'title', 'cast', 'crew']
df_movies = df_movies.merge(df_credits.drop(columns=['title']), on='id')

# Convert stringified lists into actual lists
features = ['cast', 'crew', 'keywords', 'genres']
for feature in features:
    df_movies[feature] = df_movies[feature].apply(literal_eval)

# --- PHASE 2: METADATA EXTRACTION ---

def get_director(x):
    for i in x:
        if i['job'] == 'Director':
            return i['name']
    return np.nan

def get_list(x):
    if isinstance(x, list):
        names = [i['name'] for i in x]
        if len(names) > 3:
            names = names[:3]
        return names
    return []

df_movies['director'] = df_movies['crew'].apply(get_director)
features = ['cast', 'keywords', 'genres']
for feature in features:
    df_movies[feature] = df_movies[feature].apply(get_list)

# Data Normalization: Remove spaces so 'Johnny Depp' becomes 'johnnydepp'
def clean_data(x):
    if isinstance(x, list):
        return [str.lower(i.replace(" ", "")) for i in x]
    else:
        if isinstance(x, str):
            return str.lower(x.replace(" ", ""))
        return ''

features = ['cast', 'keywords', 'director', 'genres']
for feature in features:
    df_movies[feature] = df_movies[feature].apply(clean_data)

# Create the Metadata Soup for Vectorization
def create_soup(x):
    return ' '.join(x['keywords']) + ' ' + ' '.join(x['cast']) + ' ' + x['director'] + ' ' + ' '.join(x['genres'])

df_movies['soup'] = df_movies.apply(create_soup, axis=1)

# --- PHASE 3: VECTORIZATION ---

count = CountVectorizer(stop_words='english')
count_matrix = count.fit_transform(df_movies['soup'])

# Pre-compute similarity for Title-to-Title searches
cosine_sim = cosine_similarity(count_matrix, count_matrix)

# --- PHASE 4: ENGINE LOGIC ---

def get_recommendations(user_input, cosine_sim=cosine_sim):
    """
    Original Content-Based Filter (FR2).
    """
    if user_input in df_movies['title'].values:
        idx = df_movies.index[df_movies['title'] == user_input].tolist()[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:11] 
    else:
        # Normalize input to match soup format
        cleaned_input = user_input.lower().replace(" ", "")
        user_vec = count.transform([cleaned_input])
        sim_scores = list(enumerate(cosine_similarity(user_vec, count_matrix)[0]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[0:10] 

    movie_indices = [i[0] for i in sim_scores]
    return df_movies.iloc[movie_indices]

def get_hybrid_recommendations(user, user_query, cosine_sim=cosine_sim):
    """
    Weighted Hybrid Recommendation Engine (FR4).
    Normalizes query input and applies Collaborative Filtering multiplier.
    """
    # 1. NORMALIZE USER QUERY
    # Turns "Chris Evans" into "chrisevans" to match the metadata soup
    normalized_query = user_query.lower().replace(" ", "")

    # 2. GET CONTENT-BASED BASELINE (Top 30)
    user_vec = count.transform([normalized_query])
    cb_scores = list(enumerate(cosine_similarity(user_vec, count_matrix)[0]))
    cb_scores = sorted(cb_scores, key=lambda x: x[1], reverse=True)[0:30] 
    
    movie_scores = {i[0]: i[1] for i in cb_scores}
    movie_indices = list(movie_scores.keys())
    
    # 3. COLLABORATIVE FILTERING (Dynamic Database Query)
    from users.models import Rating 
    
    ratings_qs = Rating.objects.all().values('user_id', 'movie_id', 'score')
    
    if ratings_qs.exists():
        df_ratings = pd.DataFrame.from_records(ratings_qs)
        avg_ratings = df_ratings.groupby('movie_id')['score'].mean().to_dict()
        
        for idx in movie_indices:
            tmdb_id = df_movies.iloc[idx]['id']
            if tmdb_id in avg_ratings:
                # Weighted multiplier tuned for higher sensitivity (divisor reduced to 2.0)
                crowd_multiplier = 1.0 + (avg_ratings[tmdb_id] / 2.0) 
                movie_scores[idx] = movie_scores[idx] * crowd_multiplier

    # 4. FINAL HYBRID SORTING
    hybrid_scores = sorted(movie_scores.items(), key=lambda item: item[1], reverse=True)
    top_10_indices = [i[0] for i in hybrid_scores[0:10]]
    
    return df_movies.iloc[top_10_indices]

def search_movies_by_title(query):
    """
    Manual Boolean Search module (NFR3).
    """
    if not query:
        return []
    matching_movies = df_movies[df_movies['title'].str.contains(query, case=False, na=False)]
    return matching_movies.head(20).to_dict('records')