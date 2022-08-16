# Generated by Django 3.0.11 on 2020-12-11 16:48
import json

import phonenumber_field.modelfields
from django.db import migrations

import pretix.base.models.fields


def migrate_settings(apps, schema_editor):
    Order = apps.get_model('pretixbase', 'Order')
    Event = apps.get_model('pretixbase', 'Event')
    Event_SettingsStore = apps.get_model('pretixbase', 'Event_SettingsStore')
    Event_SettingsStore.objects.filter(key='telephone_field_required').update(key='order_phone_required')
    Event_SettingsStore.objects.filter(key='telephone_field_help_text').update(key='checkout_phone_helptext')
    for e in Event.objects.filter(plugins__icontains="pretix_telephone"):
        plugins = e.plugins.split(",")
        plugins.remove("pretix_telephone")
        e.plugins = ",".join(plugins)
        e.save()
        Event_SettingsStore.objects.create(object=e, key='order_phone_asked', value='True')
    for o in Order.objects.filter(meta_info__icontains='"telephone"'):
        mi = json.loads(o.meta_info)
        if 'telephone' in mi.get('contact_form_data', {}):
            mi['phone'] = mi['contact_form_data'].pop('telephone')
            o.phone = mi['phone']
            o.meta_info = json.dumps(mi)
            o.save(update_fields=['meta_info', 'phone'])


class Migration(migrations.Migration):

    dependencies = [
        ('pretixbase', '0172_event_sales_channels'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='phone',
            field=phonenumber_field.modelfields.PhoneNumberField(max_length=128, null=True, region=None),
        ),
        migrations.AlterField(
            model_name='event',
            name='sales_channels',
            field=pretix.base.models.fields.MultiStringField(default=['web']),
        ),
        migrations.RunPython(
            migrate_settings, migrations.RunPython.noop,
        )
    ]
