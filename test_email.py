from bookingapp.models import Order

order = Order.objects.last()
print(f"Latest Order ID: {order.id}")
print(f"Customer Email: {order.customer_email}")
print(f"Status: {order.status}")
print("Trying to send email manually...")
try:
    order.send_confirmation_email()
    print("Email sent without raising exception!")
except Exception as e:
    print(f"Exception raised: {e}")
