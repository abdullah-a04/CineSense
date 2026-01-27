import pandas as pd
import numpy as np
from ast import literal_eval
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. Load the Datasets
df_movies = pd.read_csv('tmdb_5000_movies.csv')
df_credits = pd.read_csv('tmdb_5000_credits.csv')

# 2. Merge on Movie ID
df_credits.columns = ['id', 'tittle', 'cast', 'crew']
df_movies = df_movies.merge(df_credits, on='id')

# 3. Clean the JSON Columns
# These columns are stored as strings; we need to convert them to Python objects
features = ['cast', 'crew', 'keywords', 'genres']
for feature in features:
    df_movies[feature] = df_movies[feature].apply(literal_eval)

# 4. Extract Key Metadata
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

# 5. Sanitize Names (Remove spaces so 'Johnny Depp' becomes 'johnnydepp')
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

# 6. The Metadata Soup
def create_soup(x):
    return ' '.join(x['keywords']) + ' ' + ' '.join(x['cast']) + ' ' + x['director'] + ' ' + ' '.join(x['genres'])

df_movies['soup'] = df_movies.apply(create_soup, axis=1)

print("Metadata Soup Created! Here is a sample:")
print(df_movies[['title', 'soup']].head())

# 7. Vectorizing the Soup
# We use CountVectorizer to turn the text 'soup' into a matrix of numbers
count = CountVectorizer(stop_words='english')
count_matrix = count.fit_transform(df_movies['soup'])

# 8. Calculating Similarity
# This creates a giant map of how similar every movie is to every other movie
cosine_sim = cosine_similarity(count_matrix, count_matrix)

# 9. Recommendation Function
# This function takes a movie title and returns the top 10 similar movies
def get_recommendations(user_input, cosine_sim=cosine_sim):
    # 1. Check if the user input is an exact movie title in our data
    if user_input in df_movies['title'].values:
        idx = df_movies.index[df_movies['title'] == user_input].tolist()[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
    else:
        # 2. If it's NOT a title (like your survey tags), treat it as a search
        # Transform the user's tags into the same vector space as our movies
        from sklearn.feature_extraction.text import CountVectorizer
        
        # We use the existing vectorizer to transform the new user query
        count = CountVectorizer(stop_words='english')
        count_matrix = count.fit_transform(df_movies['soup'])
        user_vec = count.transform([user_input])
        
        # Calculate similarity between the user query and all movies
        from sklearn.metrics.pairwise import cosine_similarity
        sim_scores = list(enumerate(cosine_similarity(user_vec, count_matrix)[0]))

    # 3. Sort and get top results as usual
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[0:10] # Top 10 matches
    movie_indices = [i[0] for i in sim_scores]
    
    # Return the full movie objects so the dashboard can show titles and ratings
    return df_movies.iloc[movie_indices]

# 🧪 TEST THE ENGINE
print("\n--- CineSense Recommendations for 'The Dark Knight Rises' ---")
print(get_recommendations('The Dark Knight Rises'))