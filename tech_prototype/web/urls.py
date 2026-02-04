from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('coin/<str:symbol>/', views.detail, name='detail'),
    path('refresh-data/', views.refresh_database, name='refresh_data'),
]