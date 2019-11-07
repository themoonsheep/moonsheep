# Generated by Django 2.2.5 on 2019-11-05 08:52

from django.db import migrations, models
import moonsheep.users


class Migration(migrations.Migration):

    dependencies = [
        ('moonsheep', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', moonsheep.models.UserManager()),
            ],
        ),
        migrations.AddField(
            model_name='user',
            name='nickname',
            field=models.CharField(blank=True, error_messages={'unique': 'A user with that nickname already exists.'}, max_length=150, unique=True, verbose_name='username'),
        ),
    ]