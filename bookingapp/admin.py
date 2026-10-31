import os
from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html

# Import your models
from .models import RoomBooking, EventBooking, Order, TableReservation

# ---------------------------------------------------------
# 1. Food / Restaurant Order Admin
# ---------------------------------------------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Updated to reflect the actual fields used in your template
    list_display = (
        'long_order_id', 
        'customer_name', 
        'order_type', 
        'order_date', 
        'total_amount', 
        'status'
    )
    list_filter = ('status', 'order_type', 'order_date')
    
    # Updated so you can search by the custom ID or customer details
    search_fields = ('long_order_id', 'customer_name', 'customer_phone')
    
    # Allows you to quickly change the order status directly from the list view
    list_editable = ('status',) 
    
    ordering = ('-order_date',)


# ---------------------------------------------------------
# 2. Table Reservation Admin
# ---------------------------------------------------------
@admin.register(TableReservation)
class TableReservationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'table',
        'customer_name',
        'phone',
        'reservation_date',
        'reservation_time',
        'guests',
        'status',
        'created_at'
    )
    list_filter = (
        'status',
        'reservation_date',
        'table',
    )
    search_fields = (
        'customer_name',
        'phone',
        'email',
        'table__table_number',
    )
    list_editable = (
        'status',
    )
    ordering = ('-reservation_date', '-reservation_time')


# ---------------------------------------------------------
# 3. Room Booking Admin
# ---------------------------------------------------------
@admin.register(RoomBooking)
class RoomBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'room',
        'guest_name',
        'check_in',
        'check_out',
        'status',
        'payment_status',
        'total_amount',
        'download_invoice'
    )
    list_filter = (
        'status',
        'payment_status',
        'check_in'
    )
    search_fields = (
        'guest_name',
        'guest_phone',
        'guest_email',
        'room__room_number'
    )
    list_editable = (
        'status',
        'payment_status'
    )

    def download_invoice(self, obj):
        invoice_filename = f'invoice_{obj.id}.txt'
        invoice_path = os.path.join(settings.MEDIA_ROOT, 'invoices', invoice_filename)
        if os.path.exists(invoice_path):
            url = f"{settings.MEDIA_URL}invoices/{invoice_filename}"
            return format_html('<a href="{}" target="_blank" style="font-weight: 600; color: #4f46e5;">📄 View Invoice</a>', url)
        return "Not Checked Out"
    download_invoice.short_description = "Invoice"


# ---------------------------------------------------------
# 4. Event Booking Admin
# ---------------------------------------------------------
@admin.register(EventBooking)
class EventBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'hall',
        'event_name',
        'guest_name',
        'start_date',
        'status',
        'payment_status',
        'download_invoice'
    )
    list_filter = (
        'status',
        'payment_status'
    )
    search_fields = (
        'event_name',
        'guest_name',
        'hall__hall_name'
    )
    list_editable = (
        'status',
        'payment_status'
    )

    def download_invoice(self, obj):
        invoice_filename = f'event_invoice_{obj.id}.txt'
        invoice_path = os.path.join(settings.MEDIA_ROOT, 'invoices', invoice_filename)
        if os.path.exists(invoice_path):
            url = f"{settings.MEDIA_URL}invoices/{invoice_filename}"
            return format_html('<a href="{}" target="_blank" style="font-weight: 600; color: #4f46e5;">📄 View Invoice</a>', url)
        return "Not Checked Out"
    download_invoice.short_description = "Invoice"