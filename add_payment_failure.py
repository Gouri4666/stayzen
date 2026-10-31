payment_failure_code = """
@transaction.atomic
def payment_failure(request):
    if request.method == "POST":
        import json
        try:
            data = json.loads(request.body)
        except Exception:
            data = request.POST

        booking_id = data.get("booking_id")
        booking_type = data.get("booking_type")

        if not booking_id or not booking_type:
            return JsonResponse({"success": False, "message": "Missing booking ID or type."})

        try:
            if booking_type == "room":
                booking = RoomBooking.objects.filter(id=booking_id).first()
                if booking:
                    if booking.status == "Pending" and booking.payment_status == "Pending":
                        booking.delete()
                        return JsonResponse({"success": True, "message": "Pending booking cleaned up successfully."})
                    else:
                        return JsonResponse({"success": False, "message": "Booking is not in Pending status; cleanup skipped."})
                else:
                    return JsonResponse({"success": False, "message": "Booking not found."})
            elif booking_type == "event":
                booking = EventBooking.objects.filter(id=booking_id).first()
                if booking:
                    if booking.status == "Pending" and booking.payment_status == "Pending":
                        booking.delete()
                        return JsonResponse({"success": True, "message": "Pending booking cleaned up successfully."})
                    else:
                        return JsonResponse({"success": False, "message": "Booking is not in Pending status; cleanup skipped."})
                else:
                    return JsonResponse({"success": False, "message": "Booking not found."})
            else:
                return JsonResponse({"success": False, "message": "Invalid booking type for payment failure cleanup."})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error executing safe payment failure cleanup for booking {booking_id} of type {booking_type}: {e}")
            return JsonResponse({"success": False, "message": "An error occurred during payment failure cleanup."})

    return JsonResponse({"success": False, "message": "POST request required."})
"""

with open('f:/project/StayZen/bookingapp/views.py', 'a', encoding='utf-8') as f:
    f.write('\n' + payment_failure_code)
print("Successfully appended payment_failure.")
