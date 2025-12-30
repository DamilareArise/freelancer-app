from bookingApp.models import Availability

def generate_hours_slots(start_hour=7, end_hour=18):
     return [f"{hour:02d}:00" for hour in range(start_hour, end_hour + 1)]
 
 
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def create_default_availability(user):
    slots = generate_hours_slots(7, 18)

    for day in DAYS:
        Availability.objects.get_or_create(
            user=user,
            day=day,
            defaults={
                "slots": slots
            }
        )