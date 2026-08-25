from django.urls import path
from .views import health_check, plan_trip

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('plan-trip/', plan_trip, name='plan_trip'),
]
