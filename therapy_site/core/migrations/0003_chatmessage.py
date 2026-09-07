from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_remove_user_age_user_email_user_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('section', models.CharField(max_length=50)),
                ('role', models.CharField(max_length=20)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='chat_messages',
                        to='core.user',
                    ),
                ),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]