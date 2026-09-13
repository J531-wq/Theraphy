from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_rename_cover_image_to_cover_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogcomment',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='blog_comments',
                to='core.user',
            ),
        ),
    ]