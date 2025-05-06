from django.urls import path
from . import views
from .views import list_ppp_sessions, disconnect_ppp, delete_ppp

urlpatterns = [
    path('', views.index, name='index'),
    path('disconnect/<str:username>/', views.disconnect_user_view, name='disconnect_user'),
    path('toggle-auto-disconnect/<str:username>/', views.toggle_auto_disconnect, name='toggle_auto_disconnect'),
    path('enable_queue/<str:queue_name>/', views.enable_queue, name='enable_queue'),
    path('disable_queue/<str:queue_name>/', views.disable_queue, name='disable_queue'),
    path('delete_queue/<str:queue_name>/', views.delete_queue, name='delete_queue'),
    path('ppp_sessions/', list_ppp_sessions, name='list_ppp_sessions'),
    path('disconnect_ppp/<str:ppp_name>/', disconnect_ppp, name='disconnect_ppp'),
    path('delete_ppp/<str:ppp_name>/', delete_ppp, name='delete_ppp'),
] 