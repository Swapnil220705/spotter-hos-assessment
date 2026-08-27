from django.urls import path
from .views import health_check, plan_trip, location_suggestions

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('plan-trip/', plan_trip, name='plan_trip'),
    path('location-suggestions/', location_suggestions, name='location_suggestions'),
]
