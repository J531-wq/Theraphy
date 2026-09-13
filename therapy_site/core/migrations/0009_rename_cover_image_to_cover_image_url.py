from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_blog_covers_admin"),
    ]

    operations = [
        migrations.RenameField(
            model_name="blog",
            old_name="cover_image",
            new_name="cover_image_url",
        ),
    ]