from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('bookingapp', '0023_eventbooking_id_number_eventbooking_id_type_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE bookingapp_roombooking MODIFY COLUMN payment_status VARCHAR(20) NOT NULL DEFAULT 'Pending';",
            reverse_sql="ALTER TABLE bookingapp_roombooking MODIFY COLUMN payment_status ENUM('Pending', 'Confirmed', 'Failed') NOT NULL DEFAULT 'Pending';"
        ),
        migrations.RunSQL(
            sql="ALTER TABLE bookingapp_eventbooking MODIFY COLUMN payment_status VARCHAR(20) NOT NULL DEFAULT 'Pending';",
            reverse_sql="ALTER TABLE bookingapp_eventbooking MODIFY COLUMN payment_status ENUM('Pending', 'Confirmed', 'Failed') NOT NULL DEFAULT 'Pending';"
        ),
    ]
