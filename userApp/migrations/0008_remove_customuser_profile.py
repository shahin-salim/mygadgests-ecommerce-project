# Generated by Django 4.0.1 on 2022-01-11 04:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('userApp', '0007_customuser_profile_delete_pic'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='profile',
        ),
    ]
