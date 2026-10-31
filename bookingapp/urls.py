from django.urls import path
from . import views

urlpatterns = [
    path('room-booking/', views.room_booking, name='room_booking'),
    path("booked-dates/<int:room_id>/", views.booked_dates, name="booked_dates"),
    path("booked-dates/hall/<int:hall_id>/", views.hall_booked_dates, name="hall_booked_dates"),
    path("booked-dates/table/<int:table_id>/", views.table_booked_dates, name="table_booked_dates"),
    path('event-booking/', views.event_booking, name='event_booking'),
    path('room-booking-dashboard/', views.room_booking_dashboard, name='room_booking_dashboard'),
    path('event-booking-dashboard/', views.event_booking_dashboard, name='event_booking_dashboard'),
    path('food-order-dashboard/',views.food_order_dashboard,name='food_order_dashboard'),
    path('table-reservation-dashboard/',views.table_reservation_dashboard,name='table_reservation_dashboard'),
    path('food-order/',views.food_order,name='food_order'),
    path('order-confirmation/<int:order_id>/',views.order_confirmation,name='order_confirmation'),
    path('table-reservation/',views.table_reservation,name='table_reservation'),
    path('dashboard/order-confirmation/<int:order_id>/',views.order_confirmation_dashboard,name='order_confirmation_dashboard'),
    path("table-reservation-confirmation/<int:reservation_id>/",views.table_reservation_confirmation,name="table_reservation_confirmation"),
    path("table-confirmation/<int:reservation_id>/",views.table_confirmation,name="table_confirmation"),
    path("room-booking-confirmation/<int:booking_id>/", views.room_booking_confirmation, name="room_booking_confirmation"),
    path("event-booking-confirmation/<int:booking_id>/", views.event_booking_confirmation, name="event_booking_confirmation"),
    path("razorpay-callback/", views.razorpay_callback, name="razorpay_callback"),
    path("payment-failure/", views.payment_failure, name="payment_failure"),
    path("resume-payment/<str:booking_type>/<int:booking_id>/", views.resume_payment, name="resume_payment"),
    path("invoice/download/<str:booking_type>/<int:booking_id>/", views.download_invoice, name="download_invoice"),
    path("orders/toggle-serving-status/<int:order_id>/", views.toggle_serving_status, name="toggle_serving_status"),
    path("payment-start/<str:booking_type>/<str:booking_id>/", views.payment_start, name="payment_start"),
    path("api/check-email-exists/", views.api_check_email_exists, name="api_check_email"),
    
]