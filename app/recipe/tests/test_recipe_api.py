import tempfile
import os

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """Return URL for recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main Course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_ingredient(user,
                      name='Cinnamon',
                      amount=1/2,
                      unit_of_measurement='teaspoon'):
    """Create and return a sample ingredient"""
    return Ingredient.objects.create(user=user, name=name, amount=amount,
                                     unit_of_measurement=unit_of_measurement)


def sample_recipe(user, **params):
    """Create and return a sample recipe"""
    defaults = {
        'title': 'Sample Recipe',
        'time_minutes': 10,
        'price': 5.00
    }

    defaults.update(params)
    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTest(TestCase):
    """Test unauthenticated Recipe API access"""
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        resp = self.client.get(RECIPES_URL)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTest(TestCase):
    """Test authenticated recipe API access"""
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'python@pythonapp.com',
            'password1'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        resp = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_recipe_is_limited_to_user(self):
        """Test retrieving recipe for user"""
        user2 = get_user_model().objects.create_user(
            'other@pythonapp.com',
            'password2'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user)

        resp = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        resp = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 15.00
        }

        resp = self.client.post(RECIPES_URL, payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=resp.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Test creating a recipe with tags"""
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')
        payload = {
            'title': 'Oreo Cheesecake',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 20.00
        }

        resp = self.client.post(RECIPES_URL, payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=resp.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        ingredient1 = sample_ingredient(user=self.user, name='Prawns',
                                        amount=1, unit_of_measurement='pounds')
        ingredient2 = sample_ingredient(user=self.user, name='Garlic',
                                        amount=4, unit_of_measurement='cloves')

        payload = {
            'title': 'Ajillo',
            'ingredients': [ingredient1.id, ingredient2.id],
            'time_minutes': 30,
            'price': 25.00
        }

        resp = self.client.post(RECIPES_URL, payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=resp.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient1, ingredients)
        self.assertIn(ingredient2, ingredients)

    def test_partial_update_recipe(self):
        """Test updating a recipe with PATCH"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name="Pasta")
        payload = {
            'title': 'Chicken Pasta',
            'tags': [new_tag.id]
        }
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test updating a recipe with PUT"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        payload = {
            'title': 'Spaghetti Carbonara',
            'time_minutes': 25,
            'price': 5.00
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)


class RecipeImageUploadTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'python@pythonapp.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self) -> None:
        self.recipe.image.delete()

    def test_upload_image_to_recipe_successful(self):
        """Test uploading an image to a recipe is successful"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tfile:
            img = Image.new('RGB', (10, 10))
            img.save(tfile, format='JPEG')
            tfile.seek(0)
            resp = self.client.post(url, {'image': tfile}, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('image', resp.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        resp = self.client.post(url, {'image': 'notimage'}, format='multipart')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipes_by_tags(self):
        """Test ruturning recipes with specific tags"""
        recipe1 = sample_recipe(user=self.user, title='Thai curry')
        recipe2 = sample_recipe(user=self.user, title='Ajillo')
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Fish')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)

        recipe3 = sample_recipe(self.user, title='Brisket')

        resp = self.client.get(
            RECIPES_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )
        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)

        self.assertIn(serializer1.data, resp.data)
        self.assertIn(serializer2.data, resp.data)
        self.assertNotIn(serializer3.data, resp.data)

    def test_filter_recipes_by_ingredients(self):
        """Test returning recipes with specific ingredients"""
        recipe1 = sample_recipe(self.user, title='Rice and beans')
        recipe2 = sample_recipe(self.user, title='Chicken pasta')
        ingredient1 = sample_ingredient(user=self.user, name='Black Beans',
                                        amount=1, unit_of_measurement='cup')
        ingredient2 = sample_ingredient(user=self.user,
                                        name='Chicken breast', amount=2)

        recipe1.ingredients.add(ingredient1)
        recipe2.ingredients.add(ingredient2)

        recipe3 = sample_recipe(user=self.user, title='Steak and mushrooms')

        resp = self.client.get(
            RECIPES_URL,
            {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        )

        serializer1 = RecipeSerializer(recipe1)
        serializer2 = RecipeSerializer(recipe2)
        serializer3 = RecipeSerializer(recipe3)
        self.assertIn(serializer1.data, resp.data)
        self.assertIn(serializer2.data, resp.data)
        self.assertNotIn(serializer3.data, resp.data)
