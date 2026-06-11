from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('chat/', views.chat_view, name='chat'),
    path('reset/', views.reset_view, name='reset'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
]
