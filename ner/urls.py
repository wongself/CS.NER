from django.urls import path

from . import views
# from .application import entity

urlpatterns = [
    path('', views.index, name='index'),
    # path('entity_query', entity.entity_query, name='entity_query'),
]