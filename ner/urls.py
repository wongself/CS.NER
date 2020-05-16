from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('entity_query/', views.entity_query, name='entity_query'),
]