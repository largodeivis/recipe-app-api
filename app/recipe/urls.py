from django.urls import path, include
from rest_framework.routers import DefaultRouter

from recipe import views

"""Default Router automatically registers the appropriate urls for all of the
actions in our viewset. ie:
/api/recipe/tags
/api/recipe/tags/{tag_id}
"""
router = DefaultRouter()
router.register('tags', views.TagViewSet)
router.register('ingredients', views.IngredientViewSet)

app_name = 'recipe'

urlpatterns = [
    path('', include(router.urls))
]
