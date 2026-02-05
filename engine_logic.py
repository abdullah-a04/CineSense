import pandas as pd
import numpy as np
from ast import literal_eval
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# This Loads the Datasets
df_movies = pd.read_csv('tmdb_5000_movies.csv')
df_credits = pd.read_csv('tmdb_5000_credits.csv')

# Merge on Movie ID
df_credits.columns = ['id', 'tittle', 'cast', 'crew']
df_movies = df_movies.merge(df_credits, on='id')

# Preprocess the Data
# Convert stringified lists into actual lists
features = ['cast', 'crew', 'keywords', 'genres']
for feature in features:
    df_movies[feature] = df_movies[feature].apply(literal_eval)

# Extract Key Metadata
def get_director(x):
    for i in x:
        if i['job'] == 'Director':
            return i['name']
    return np.nan

def get_list(x):
    if isinstance(x, list):
        names = [i['name'] for i in x]
        # Return top 3 elements
        if len(names) > 3:
            names = names[:3]
        return names
    return []

df_movies['director'] = df_movies['crew'].apply(get_director)
features = ['cast', 'keywords', 'genres']
for feature in features:
    df_movies[feature] = df_movies[feature].apply(get_list)

# Remove spaces so 'Johnny Depp' becomes 'johnnydepp'
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

# The Metadata Soup
def create_soup(x):
    return ' '.join(x['keywords']) + ' ' + ' '.join(x['cast']) + ' ' + x['director'] + ' ' + ' '.join(x['genres'])

df_movies['soup'] = df_movies.apply(create_soup, axis=1)

print("Metadata Soup Created! Here is a sample:")
print(df_movies[['title', 'soup']].head())


# We use CountVectorizer to turn the text 'soup' into a matrix of numbers
count = CountVectorizer(stop_words='english')
count_matrix = count.fit_transform(df_movies['soup'])


# This creates a giant map of how similar every movie is to every other movie
cosine_sim = cosine_similarity(count_matrix, count_matrix)


# This function takes a movie title and returns the top 10 similar movies
def get_recommendations(user_input, cosine_sim=cosine_sim):
    if user_input in df_movies['title'].values:
        idx = df_movies.index[df_movies['title'] == user_input].tolist()[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
    else:
        
        # Transforms the user's tags into the same vector space as our movies
        from sklearn.feature_extraction.text import CountVectorizer
        
        # This uses the existing vectorizer to transform the new user query
        count = CountVectorizer(stop_words='english')
        count_matrix = count.fit_transform(df_movies['soup'])
        user_vec = count.transform([user_input])
        
        # Calculates similarity between the user query and all movies
        from sklearn.metrics.pairwise import cosine_similarity
        sim_scores = list(enumerate(cosine_similarity(user_vec, count_matrix)[0]))

    # Sort and get top results as usual
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[0:10] # Top 10 matches
    movie_indices = [i[0] for i in sim_scores]
    
    # Return the full movie objects so the dashboard can show titles and ratings
    return df_movies.iloc[movie_indices]

# TEST THE ENGINE
print("\n--- CineSense Recommendations for 'The Dark Knight Rises' ---")
print(get_recommendations('The Dark Knight Rises'))