# Generated by Django 3.2.9 on 2021-12-07 10:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='home',
            name='admin',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.PROTECT, to='budget.account'),
        ),
    ]
