# Generated by Django 3.2 on 2022-02-01 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adminApp', '0015_rename_product_id_banner_p_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='offer',
            field=models.IntegerField(default=0),
        ),
    ]
