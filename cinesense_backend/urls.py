from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView # Add this import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')), # Connects the app routes (survey, home)
    path('accounts/', include('django.contrib.auth.urls')), # Adds login, logout
    
    # THE FIX: Catch empty URLs and seamlessly redirect to the home page
    path('', RedirectView.as_view(pattern_name='home', permanent=False), name='index'), 
]