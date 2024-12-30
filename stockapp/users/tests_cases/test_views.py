from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class HomeViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        return super().setUpTestData()

    def setUp(self):
        return super().setUp()
    
    def test_url_exists_at_desired_location(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_url_exists_at_desired_name(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
    
    def test_template_used(self):
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

    @classmethod
    def setUpTestData(cls):
        return super().setUpTestData()
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword2203@')
        self.login_url = reverse('account_login')
        self.home_url = reverse('home')
        return super().setUp()

    def test_url_exists_at_desired_location(self):
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
    
    def test_view_redirect_if_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.get(self.login_url)
        self.assertRedirects(response, self.home_url)
    
    def test_template_used(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')
