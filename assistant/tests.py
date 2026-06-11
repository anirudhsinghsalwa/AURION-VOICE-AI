import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
import django.test.client
from copy import copy

# Workaround for Python 3.14 compatibility with Django 5.0 test context copy
original_store_rendered_templates = django.test.client.store_rendered_templates

def safe_store_rendered_templates(store, signal, sender, template, context, **kwargs):
    store.setdefault("templates", []).append(template)
    if "context" not in store:
        store["context"] = django.test.client.ContextList()
    try:
        store["context"].append(copy(context))
    except AttributeError:
        # Fallback for Python 3.14 context copy bug in Django 5.0
        store["context"].append(context)

django.test.client.store_rendered_templates = safe_store_rendered_templates


class AssistantViewsTestCase(TestCase):
    
    def setUp(self):
        self.username = "testuser"
        self.password = "password123"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        
    def test_login_page_renders(self):
        """Verify the login page renders successfully."""
        response = self.client.get(reverse('assistant:login'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome Back', response.content)
        
    def test_register_page_renders(self):
        """Verify the register page renders successfully."""
        response = self.client.get(reverse('assistant:register'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create Account', response.content)

    def test_login_success(self):
        """Verify that logging in with valid credentials redirects to index."""
        response = self.client.post(reverse('assistant:login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertRedirects(response, reverse('assistant:index'))

    def test_register_success(self):
        """Verify user registration creates user and redirects to index."""
        response = self.client.post(reverse('assistant:register'), {
            'username': 'newuser',
            'password': 'password123',
            'password_confirm': 'password123'
        })
        self.assertRedirects(response, reverse('assistant:index'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_index_view_redirects_anonymous(self):
        """Verify that index redirects to login for unauthenticated users."""
        response = self.client.get(reverse('assistant:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_index_view_authenticated(self):
        """Verify homepage loads for authenticated users."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('assistant:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AURION', response.content)

    @patch('assistant.views.get_gemini_response')
    def test_chat_view_success(self, mock_gemini):
        """Verify chat view responses and updates conversation history."""
        mock_gemini.return_value = "Hello! I am Aurion."
        self.client.login(username=self.username, password=self.password)
        
        response = self.client.post(
            reverse('assistant:chat'), 
            data=json.dumps({'message': 'Hello'}), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['reply'], "Hello! I am Aurion.")
        
        history = self.client.session['chat_history']
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['content'], 'Hello')
        self.assertEqual(history[1]['content'], "Hello! I am Aurion.")

    def test_reset_view(self):
        """Verify reset endpoint clears session history."""
        self.client.login(username=self.username, password=self.password)
        
        # Manually populate session history
        session = self.client.session
        session['chat_history'] = [{'role': 'user', 'content': 'Hi'}]
        session.save()
        
        response = self.client.post(reverse('assistant:reset'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.client.session['chat_history']), 0)
