# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-02-03 14:21
from __future__ import unicode_literals

import django.core.validators
import django.db.migrations.operations.special
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import pretix.base.validators


def preserve_event_settings(apps, schema_editor):
    Event = apps.get_model('pretixbase', 'Event')
    EventSetting = apps.get_model('pretixbase', 'EventSetting')
    for e in Event.objects.all():
        EventSetting.objects.create(object=e, key='mail_days_order_expire_warning', value='0')


def forwards42(apps, schema_editor):
    Order = apps.get_model('pretixbase', 'Order')
    EventSetting = apps.get_model('pretixbase', 'EventSetting')
    etz = {
        s['object_id']: s['value']
        for s in EventSetting.objects.filter(key='timezone').values('object_id', 'value')
        }
    for order in Order.objects.all():
        tz = pytz.timezone(etz.get(order.event_id, 'UTC'))
        order.expires = order.expires.astimezone(tz).replace(hour=23, minute=59, second=59)
        order.save()


def forwards44(apps, schema_editor):
    CachedTicket = apps.get_model('pretixbase', 'CachedTicket')
    CachedTicket.objects.all().delete()


class Migration(migrations.Migration):

    replaces = [('pretixbase', '0031_auto_20160816_0648'), ('pretixbase', '0032_question_position'), ('pretixbase', '0033_auto_20160821_2222'), ('pretixbase', '0034_auto_20160830_1952'), ('pretixbase', '0032_item_allow_cancel'), ('pretixbase', '0033_auto_20160822_1044'), ('pretixbase', '0035_merge'), ('pretixbase', '0036_auto_20160902_0755'), ('pretixbase', '0037_invoice_payment_provider_text'), ('pretixbase', '0038_auto_20160924_1448'), ('pretixbase', '0039_user_require_2fa'), ('pretixbase', '0040_u2fdevice'), ('pretixbase', '0041_auto_20161018_1654'), ('pretixbase', '0042_order_expires'), ('pretixbase', '0043_globalsetting'), ('pretixbase', '0044_auto_20161101_1610'), ('pretixbase', '0045_auto_20161108_1542'), ('pretixbase', '0046_order_meta_info'), ('pretixbase', '0047_auto_20161126_1300'), ('pretixbase', '0048_auto_20161129_1330')]

    dependencies = [
        ('pretixbase', '0030_auto_20160816_0646'),
    ]

    operations = [
        migrations.RenameField(
            model_name='invoice',
            old_name='invoice_no_charfield',
            new_name='invoice_no',
        ),
        migrations.AddField(
            model_name='invoice',
            name='footer_text',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='introductory_text',
            field=models.TextField(blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together=set([('event', 'invoice_no')]),
        ),
        migrations.AddField(
            model_name='question',
            name='position',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='question',
            options={'ordering': ('position', 'id'), 'verbose_name': 'Question', 'verbose_name_plural': 'Questions'},
        ),
        migrations.AddField(
            model_name='item',
            name='allow_cancel',
            field=models.BooleanField(default=True, help_text='If you deactivate this, an order including this product might not be cancelled by the user. It may still be cancelled by you.', verbose_name='Allow product to be cancelled'),
        ),
        migrations.AddField(
            model_name='order',
            name='expiry_reminder_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            code=preserve_event_settings,
        ),
        migrations.AddField(
            model_name='invoice',
            name='payment_provider_text',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='eventpermission',
            name='can_view_vouchers',
            field=models.BooleanField(default=True, verbose_name='Can view vouchers'),
        ),
        migrations.AlterField(
            model_name='item',
            name='allow_cancel',
            field=models.BooleanField(default=True, help_text='If you deactivate this, an order including this product might not be canceled by the user. It may still be canceled by you.', verbose_name='Allow product to be canceled'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('n', 'pending'), ('p', 'paid'), ('e', 'expired'), ('c', 'canceled'), ('r', 'refunded')], db_index=True, max_length=3, verbose_name='Status'),
        ),
        migrations.AddField(
            model_name='user',
            name='require_2fa',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='U2FDevice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The human-readable name of this device.', max_length=64)),
                ('confirmed', models.BooleanField(default=True, help_text='Is this device ready for use?')),
                ('json_data', models.TextField()),
                ('user', models.ForeignKey(help_text='The user that this device belongs to.', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='cachedticket',
            name='cachedfile',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='pretixbase.CachedFile'),
        ),
        migrations.RunPython(
            code=forwards42,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.CreateModel(
            name='GlobalSetting',
            fields=[
                ('key', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('value', models.TextField()),
            ],
        ),
        migrations.RunPython(
            code=forwards44,
            reverse_code=django.db.migrations.operations.special.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='cachedticket',
            name='order',
        ),
        migrations.AddField(
            model_name='cachedticket',
            name='order_position',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='pretixbase.OrderPosition'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='cartposition',
            name='expires',
            field=models.DateTimeField(db_index=True, verbose_name='Expiration date'),
        ),
        migrations.AlterField(
            model_name='voucher',
            name='redeemed',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Redeemed'),
        ),
        migrations.AlterField(
            model_name='voucher',
            name='valid_until',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Valid until'),
        ),
        migrations.AddField(
            model_name='order',
            name='meta_info',
            field=models.TextField(blank=True, null=True, verbose_name='Meta information'),
        ),
        migrations.AddField(
            model_name='voucher',
            name='max_usages',
            field=models.PositiveIntegerField(default=1, help_text='Number of times this voucher can be redeemed.', verbose_name='Maximum usages'),
        ),
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.CharField(max_length=50, db_index=True, help_text='Should be short, only contain lowercase letters and numbers, and must be unique among your events. This is being used in addresses and bank transfer references.', validators=[django.core.validators.RegexValidator(message='The slug may only contain letters, numbers, dots and dashes.', regex='^[a-zA-Z0-9.-]+$'), pretix.base.validators.EventSlugBanlistValidator()], verbose_name='Slug'),
        ),
        migrations.AlterField(
            model_name='organizer',
            name='slug',
            field=models.CharField(max_length=50, db_index=True, help_text='Should be short, only contain lowercase letters and numbers, and must be unique among your events. This is being used in addresses and bank transfer references.', validators=[django.core.validators.RegexValidator(message='The slug may only contain letters, numbers, dots and dashes.', regex='^[a-zA-Z0-9.-]+$'), pretix.base.validators.OrganizerSlugBanlistValidator()], verbose_name='Slug'),
        ),
        migrations.AlterField(
            model_name='voucher',
            name='redeemed',
            field=models.PositiveIntegerField(default=0, verbose_name='Redeemed'),
        ),
        migrations.AddField(
            model_name='voucher',
            name='price_mode',
            field=models.CharField(choices=[('none', 'No effect'), ('set', 'Set product price to'), ('subtract', 'Subtract from product price'), ('percent', 'Reduce product price by (%)')], default='set', max_length=100, verbose_name='Price mode'),
        ),
        migrations.RenameField(
            model_name='voucher',
            old_name='price',
            new_name='value',
        ),
        migrations.AlterField(
            model_name='voucher',
            name='value',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Voucher value'),
        ),
    ]