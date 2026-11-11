from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_pageview'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='moderation_reason',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Reason provided by an admin when a published post is removed.',
            ),
        ),
    ]
