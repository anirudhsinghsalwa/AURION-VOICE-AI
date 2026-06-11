import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .gemini_service import get_gemini_response

logger = logging.getLogger(__name__)

@ensure_csrf_cookie
def index_view(request):
    """
    Renders the assistant interface. Establishes the CSRF cookie
    and passes the session-based chat history to the template.
    """
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
    
    context = {
        'chat_history': request.session['chat_history']
    }
    return render(request, 'index.html', context)


def chat_view(request):
    """
    POST API endpoint for conversational queries.
    Accepts JSON input: {"message": "user speech/text"}
    Returns JSON output: {"reply": "gemini speech/text"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    # Fetch existing chat history from Django session
    history = request.session.get('chat_history', [])

    # Call the Gemini service to retrieve a response
    reply = get_gemini_response(user_message, history)

    # Append the turn to the session history
    history.append({'role': 'user', 'content': user_message})
    history.append({'role': 'model', 'content': reply})
    
    # Persist updated session history
    request.session['chat_history'] = history
    request.session.modified = True

    return JsonResponse({'reply': reply})


def reset_view(request):
    """
    POST API endpoint to clear the conversation memory.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)
    
    request.session['chat_history'] = []
    request.session.modified = True
    return JsonResponse({'status': 'success', 'message': 'Conversation history cleared.'})
