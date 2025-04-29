from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('disconnect/<str:username>/', views.disconnect_user_view, name='disconnect_user'),
    path('toggle-auto-disconnect/<str:username>/', views.toggle_auto_disconnect, name='toggle_auto_disconnect'),
] 