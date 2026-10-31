content = open('templates/admin/bookings/offline_event_booking.html', encoding='utf-8').read()
lines = content.splitlines()
for idx in range(189, min(len(lines), 220)):
    print(f"Line {idx+1}: {lines[idx]}")
