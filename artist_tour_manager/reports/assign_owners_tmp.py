from django.contrib.auth.models import User
from tours.models import Artist
import random

users = [
    ("jimin_song", "jimin.song@example.com"),
    ("asv_tours", "asv.tours@example.com"),
    ("ppe_entertainment", "ppe.ent@example.com"),
]

created_users = 0
user_objs = []
for username, email in users:
    user, was_created = User.objects.get_or_create(username=username, defaults={"email": email})
    if was_created:
        user.set_password("demo1234!")
        user.save()
        created_users += 1
    user_objs.append(user)

artists = Artist.objects.filter(owner__isnull=True)
assigned = 0
for artist in artists:
    artist.owner = random.choice(user_objs)
    artist.save()
    assigned += 1

print(f"users_created={created_users} artists_assigned={assigned}")
