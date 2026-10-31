from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('bookingapp', '0006_alter_eventbooking_status'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS trg_eventbooking_payment_status_confirm_update;
            """,
            reverse_sql=""
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER trg_eventbooking_payment_status_confirm_update
            BEFORE UPDATE ON bookingapp_eventbooking
            FOR EACH ROW
            BEGIN
                IF NEW.payment_status = 'Confirmed' AND NEW.status = 'Pending' THEN
                    SET NEW.status = 'Confirmed';
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS trg_eventbooking_payment_status_confirm_update;"
        ),
        migrations.RunSQL(
            sql="""
            DROP TRIGGER IF EXISTS trg_eventbooking_payment_status_confirm_insert;
            """,
            reverse_sql=""
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER trg_eventbooking_payment_status_confirm_insert
            BEFORE INSERT ON bookingapp_eventbooking
            FOR EACH ROW
            BEGIN
                IF NEW.payment_status = 'Confirmed' AND NEW.status = 'Pending' THEN
                    SET NEW.status = 'Confirmed';
                END IF;
            END;
            """,
            reverse_sql="DROP TRIGGER IF EXISTS trg_eventbooking_payment_status_confirm_insert;"
        ),
    ]
