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
    
    def test_index_view_loads(self):
        """Verify the index page loads successfully."""
        response = self.client.get(reverse('assistant:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AURION', response.content)

    @patch('assistant.views.get_gemini_response')
    def test_chat_view_success(self, mock_gemini):
        """Verify chat view responses and updates conversation history."""
        mock_gemini.return_value = "Hello! I am Aurion."
        
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
        # Manually populate session history
        session = self.client.session
        session['chat_history'] = [{'role': 'user', 'content': 'Hi'}]
        session.save()
        
        response = self.client.post(reverse('assistant:reset'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.client.session['chat_history']), 0)
