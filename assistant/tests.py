import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
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
    
    def test_index_view(self):
        """
        Verify the homepage loads successfully and initializes the session.
        """
        url = reverse('assistant:index')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AURION', response.content)
        self.assertIn('chat_history', self.client.session)
        self.assertEqual(len(self.client.session['chat_history']), 0)


    @patch('assistant.views.get_gemini_response')
    def test_chat_view_success(self, mock_gemini):
        """
        Verify that POSTing a valid message to `/chat/` gets the Gemini reply
        and updates the conversation history session state.
        """
        # Configure mock behavior
        mock_gemini.return_value = "Hello! I am Aurion, how can I help you?"
        
        url = reverse('assistant:chat')
        data = {'message': 'Hello assistant'}
        
        response = self.client.post(
            url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['reply'], "Hello! I am Aurion, how can I help you?")
        
        # Verify session state was updated with user prompt and model response
        session_history = self.client.session['chat_history']
        self.assertEqual(len(session_history), 2)
        self.assertEqual(session_history[0]['role'], 'user')
        self.assertEqual(session_history[0]['content'], 'Hello assistant')
        self.assertEqual(session_history[1]['role'], 'model')
        self.assertEqual(session_history[1]['content'], "Hello! I am Aurion, how can I help you?")

    def test_chat_view_empty_message(self):
        """
        Verify that posting an empty message returns a 400 Bad Request error.
        """
        url = reverse('assistant:chat')
        data = {'message': ''}
        
        response = self.client.post(
            url, 
            data=json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)

    def test_chat_view_invalid_json(self):
        """
        Verify that posting malformed JSON returns a 400 error.
        """
        url = reverse('assistant:chat')
        
        response = self.client.post(
            url, 
            data="invalid-json-content", 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)

    @patch('assistant.views.get_gemini_response')
    def test_reset_view(self, mock_gemini):
        """
        Verify that resetting the conversation clears the chat history.
        """
        mock_gemini.return_value = "Mock response"
        
        # Call chat to establish some history
        chat_url = reverse('assistant:chat')
        self.client.post(chat_url, data=json.dumps({'message': 'Query'}), content_type='application/json')
        
        self.assertEqual(len(self.client.session['chat_history']), 2)
        
        # Reset the session history
        reset_url = reverse('assistant:reset')
        response = self.client.post(reset_url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        
        # Verify history is now empty
        self.assertEqual(len(self.client.session['chat_history']), 0)
