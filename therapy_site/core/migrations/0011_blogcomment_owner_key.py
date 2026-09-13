from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_blogcomment_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='blogcomment',
            name='owner_key',
            field=models.CharField(
                blank=True, default='', db_index=True, max_length=64
            ),
        ),
    ]