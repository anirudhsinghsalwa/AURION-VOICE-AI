import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from .gemini_service import get_gemini_response

logger = logging.getLogger(__name__)


@login_required(login_url='assistant:login')
@ensure_csrf_cookie
def index_view(request):
    """
    Renders the assistant interface for logged-in users.
    Establishes the CSRF cookie and passes the session-based chat history.
    """
    if 'chat_history' not in request.session:
        request.session['chat_history'] = []
    
    context = {
        'chat_history': request.session['chat_history']
    }
    return render(request, 'index.html', context)


@login_required(login_url='assistant:login')
def chat_view(request):
    """
    POST API endpoint for conversational queries.
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


@login_required(login_url='assistant:login')
def reset_view(request):
    """
    POST API endpoint to clear the conversation memory.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed.'}, status=405)
    
    request.session['chat_history'] = []
    request.session.modified = True
    return JsonResponse({'status': 'success', 'message': 'Conversation history cleared.'})


def login_view(request):
    """
    Handles user login.
    """
    if request.user.is_authenticated:
        return redirect('assistant:index')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Re-initialize history on fresh login
            request.session['chat_history'] = []
            return redirect('assistant:index')
        else:
            error = "Invalid username or password."
            
    return render(request, 'login.html', {'error': error})


def register_view(request):
    """
    Handles user registration.
    """
    if request.user.is_authenticated:
        return redirect('assistant:index')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        if not username or not password or not email:
            error = "All fields are required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != password_confirm:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "Username is already taken."
        else:
            try:
                user = User.objects.create_user(username=username, email=email, password=password)
                login(request, user)
                request.session['chat_history'] = []
                return redirect('assistant:index')
            except Exception as e:
                error = f"Error creating account: {str(e)}"

                
    return render(request, 'register.html', {'error': error})


def logout_view(request):
    """
    Logs out the user and redirects to the login page.
    """
    logout(request)
    return redirect('assistant:login')
