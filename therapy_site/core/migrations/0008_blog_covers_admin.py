# Generated — assigns "Admin" authorship + real Unsplash cover photos to the
# 25 seeded blog posts (5 per category).

from django.db import migrations


BASE = "https://images.unsplash.com/{}?q=80&w=1200&auto=format&fit=crop"

# (slug, unsplash_photo_id) — in the seeded-post order.
COVERS = [
    # Therapy
    ("first-therapy-session-what-to-expect", "photo-1573497620053-ea5300f94f21"),
    ("online-therapy-vs-in-person-honest-comparison", "photo-1588196749597-9ff075ee6b5b"),
    ("how-to-tell-if-therapy-is-working", "photo-1506126613408-eca07ce68773"),
    ("cbt-explained-in-plain-english", "photo-1499750310107-5fef28a66643"),
    ("support-a-friend-who-started-therapy", "photo-1521791136064-7986c2920216"),
    # Mental Health
    ("high-functioning-anxiety-struggle-nobody-sees", "photo-1493836512294-502baa1986e2"),
    ("burnout-or-depression-tell-the-difference", "photo-1500530855697-b586d89ba3ee"),
    ("why-your-brain-catastrophizes-at-3am", "photo-1515696955266-4f67e13219e0"),
    ("what-endless-scrolling-does-to-your-mood", "photo-1512941937669-90a1b58e7e9c"),
    ("asking-for-help-isnt-weakness-its-a-skill", "photo-1544027993-37dbfe43562a"),
    # Wellness
    ("sleep-mood-connection-what-one-bad-night-costs", "photo-1541781774459-bb2af2f05b55"),
    ("twenty-minute-walk-beats-perfect-routine", "photo-1476480862126-209bfaa8edc8"),
    ("digital-sunset-evenings-that-actually-rest-you", "photo-1470252649378-9c29740c9fa8"),
    ("journaling-that-actually-helps", "photo-1455390582262-044cdead277a"),
    ("food-and-mood-small-changes", "photo-1490645935967-10de6ba17061"),
    # Tips & Advice
    ("five-minute-reset-for-anxious-moments", "photo-1499209974431-9dddcece7f88"),
    ("set-boundaries-without-guilt-spiral", "photo-1529156069898-49953e39b3ac"),
    ("what-to-say-when-someones-having-a-hard-day", "photo-1573497019940-1c28c88b4f3e"),
    ("procrastination-isnt-laziness-its-emotional", "photo-1484480974693-6ca0a78fb36b"),
    ("tiny-habits-why-small-beats-big", "photo-1434682881908-b43d0467b798"),
    # Success Stories
    ("sarah-story-sixty-minutes", "photo-1544367567-0f2fcb009e0b"),
    ("marcus-story-living-alongside-panic", "photo-1507003211169-0a1dd7228f2d"),
    ("maya-story-getting-through-senior-year", "photo-1523240795612-9a054b0db644"),
    ("ben-and-priya-story-ten-conversations", "photo-1516589178581-6cd7833ae3b2"),
    ("anna-story-carrying-grief", "photo-1470071459604-3b5ec3a7fe05"),
]


def assign_covers_and_authors(apps, schema_editor):
    Blog = apps.get_model("core", "Blog")
    for slug, photo_id in COVERS:
        Blog.objects.filter(slug=slug).update(
            author="Admin", cover_image=BASE.format(photo_id)
        )


def reverse_noop(apps, schema_editor):
    # Keep seeded data on reverse (posts survive migrate-back too).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_blogsubscriber_blog_cover_image_url_blog_likes_count_and_more"),
    ]

    operations = [
        migrations.RunPython(assign_covers_and_authors, reverse_noop),
    ]
