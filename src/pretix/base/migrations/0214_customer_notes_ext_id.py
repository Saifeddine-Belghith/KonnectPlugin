# Generated by Django 3.2.12 on 2022-04-28 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pretixbase', '0213_discount_condition_ignore_voucher_discounted'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='external_identifier',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='customer',
            name='notes',
            field=models.TextField(null=True),
        ),
    ]
