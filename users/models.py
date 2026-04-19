from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    survey_completed = models.BooleanField(default=False)
    
    # The 7 Elicitation Fields
    favorite_genres = models.TextField(blank=True)
    preferred_era = models.CharField(max_length=50, blank=True)
    favorite_actors = models.TextField(blank=True)
    favorite_directors = models.TextField(blank=True)
    animation_pref = models.CharField(max_length=50, blank=True)
    language_pref = models.CharField(max_length=50, blank=True)
    favorite_movie = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# This ensures a profile is created every time a new User is registered
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    movie_id = models.IntegerField() # The bridge to your TMDB Pandas DataFrame
    movie_title = models.CharField(max_length=255) # Stored for faster frontend UI rendering
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevents a user from adding the same movie to their watchlist twice
        unique_together = ('user', 'movie_id')

    def __str__(self):
        return f"{self.user.username} wants to watch {self.movie_title}"

class Rating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings')
    movie_id = models.IntegerField() # The bridge to your TMDB Pandas DataFrame
    movie_title = models.CharField(max_length=255)
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevents a user from leaving multiple conflicting ratings on the same movie
        unique_together = ('user', 'movie_id')

    def __str__(self):
        return f"{self.user.username} rated {self.movie_title} {self.score} Stars"    