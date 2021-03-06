# Generated by Django 3.2 on 2022-02-16 04:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('adminApp', '0025_alter_category_offer'),
        ('userApp', '0029_auto_20220209_0636'),
    ]

    operations = [
        migrations.CreateModel(
            name='whishlist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adminApp.variantandprice')),
                ('user_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
