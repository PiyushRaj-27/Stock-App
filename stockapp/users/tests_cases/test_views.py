"""
This module contains the tests for the users app.
It handles test of user-related actions such as login, logout, and profile management.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class HomeViewTest(TestCase):
    """ Test module for Home View """

    def test_url_exists_at_desired_location(self):
        """Test if the home page exists at the desired location"""

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_url_exists_at_desired_name(self):
        """Test if the home page exists at the desired name"""

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_template_used(self):
        """Test if the correct template is used for the home page"""

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')


    # apparently we cannot test this because during testing django does not server static file
    # def test_css_loaded(self):
    #     response = self.client.get(reverse('home'))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, '/static/users/css/home.css')
    #     self.assertContains(response, '/static/css/base.css')

    #     response = self.client.get("/static/users/css/home.css")
    #     self.assertIn(response.status_code, [200, 304])

    #     response = self.client.get("/static/css/base.css")
    #     self.assertIn(response.status_code, [200, 304])


class TestLoginView(TestCase):
    """Test module for login view"""

    def setUp(self):
        """Creats a user for testing"""

        self.user = User.objects.create_user(username='testuser', password='testpassword2203@')
        self.login_url = reverse('account_login')
        self.home_url = reverse('home')

    def test_url_exists_at_desired_location(self):
        """Test if the login page exists at the desired location"""

        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)

    def test_view_redirect_if_logged_in(self):
        """Test if the login page redirects to home page if user is logged in"""

        self.client.force_login(self.user)
        response = self.client.get(self.login_url)
        self.assertRedirects(response, self.home_url)

    def test_template_used(self):
        """Test if the correct template is used for the login page"""

        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')


class TestSignupView(TestCase):
    """Test module for signup view"""


    def setUp(self):
        """Creats a user for testing"""

        self.user = User.objects.create_user(username='testuser', password='testpassword2203@')
        self.signup_url = reverse('account_signup')
        self.home_url = reverse('home')
        return super().setUp()

    def test_url_exists_at_desired_location(self):
        """Test if the signup page exists at the desired location"""

        response = self.client.get(reverse('account_signup'))
        self.assertEqual(response.status_code, 200)

    def test_view_redirect_if_logged_in(self):
        """Test if the signup page redirects to home page if user is logged in"""

        self.client.force_login(self.user)
        response = self.client.get(self.signup_url)
        self.assertRedirects(response, self.home_url)
    