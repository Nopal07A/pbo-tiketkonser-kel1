from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('event/<uuid:event_id>/', views.event_detail, name='event_detail'),
    path('book/<uuid:category_id>/', views.book_ticket, name='book_ticket'),
    path('checkout/<uuid:order_id>/', views.checkout, name='checkout'),
    path('pay/<uuid:order_id>/', views.pay_order, name='pay_order'),
    path('history/', views.ticket_history, name='ticket_history'),
    path('forums/', views.forum_list, name='forum_list'),
    path('forums/<uuid:event_id>/', views.forum_room, name='forum_room'),
    path('forums/message/<int:message_id>/delete/', views.delete_forum_message, name='delete_forum_message'),
    
    path('register/', views.register, name='register'),
]