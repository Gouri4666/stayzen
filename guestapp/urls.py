from django.urls import path
from . import views
from bookingapp.views import book_activity_session, track_restaurant_order

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('rooms/', views.rooms, name='rooms'),
    path('rooms/<int:room_id>/', views.room_detail, name='room_detail'),

    path('event/', views.event, name='event'),
    path('activities/',views.activity,name='activity'),
    path('activity/<int:id>/',views.activity_detail,name='activity_detail'),
    path('activity/book/<int:activity_id>/', book_activity_session, name='book_activity_session'),
    path('food-menu/', views.food_menu, name='food_menu'),
    path('hall-packages/<int:hall_id>/',views.hall_packages,name='hall_packages'),
    path('cart/', views.view_cart, name='view_cart'),
    path('add-to-cart/<int:food_id>/', views.add_to_cart, name='add_to_cart'),
    path('increase-cart/<int:food_id>/', views.increase_cart, name='increase_cart'),
    path('decrease-cart/<int:food_id>/', views.decrease_cart, name='decrease_cart'),
    path('remove-from-cart/<int:food_id>/',views.remove_from_cart,name='remove_from_cart'),
    path('tables/',views.table_list_guest,name='table_list_guest'),
    path('order-now/<int:food_id>/',views.order_now,name='order_now'),
    path('category/<str:category_name>/', views.category_detail, name='category_detail'),
    path('track-food/<str:long_order_id>/', views.track_food_order, name='track_food_order'),
    path('booking/track/<str:tracking_token>/', views.track_booking, name='track_booking'),
    path('booking/cancel/<str:tracking_token>/', views.cancel_booking, name='cancel_booking'),
    path('restaurant/track/<str:tracking_token>/', track_restaurant_order, name='track_restaurant_order'),
    path('feedback/',views.feedback_view,name='feedback'),
    path('api/check-phone/', views.api_check_phone, name='api_check_phone'),
]