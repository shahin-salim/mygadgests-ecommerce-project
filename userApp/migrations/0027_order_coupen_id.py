# Generated by Django 3.2 on 2022-02-03 02:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('adminApp', '0019_coupen'),
        ('userApp', '0026_alter_order_variant_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='coupen_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='adminApp.coupen'),
        ),
    ]