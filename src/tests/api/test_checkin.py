#
# This file is part of pretix (Community Edition).
#
# Copyright (C) 2014-2020 Raphael Michel and contributors
# Copyright (C) 2020-2021 rami.io GmbH and contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation in version 3 of the License.
#
# ADDITIONAL TERMS APPLY: Pursuant to Section 7 of the GNU Affero General Public License, additional terms are
# applicable granting you additional permissions and placing additional restrictions on your usage of this software.
# Please refer to the pretix LICENSE file to obtain the full terms applicable to this work. If you did not receive
# this file, see <https://pretix.eu/about/en/license>.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.
#
import datetime
import time
from decimal import Decimal
from unittest import mock
# deprecated: from django.utils.http import urlquote
# use urlib instead
from urllib.parse import quote as urlquote

import pytest
from django.core.files.base import ContentFile
from django.utils.timezone import now
from django_countries.fields import Country
from django_scopes import scopes_disabled
from i18nfield.strings import LazyI18nString
from pytz import UTC

from pretix.api.serializers.item import QuestionSerializer
from pretix.base.models import (
    Checkin, CheckinList, InvoiceAddress, Order, OrderPosition,
)


@pytest.fixture
def item(event):
    return event.items.create(name="Budget Ticket", default_price=23)


@pytest.fixture
def item_on_wrong_event(event2):
    return event2.items.create(name="Budget Ticket", default_price=23)


@pytest.fixture
def other_item(event):
    return event.items.create(name="Budget Ticket", default_price=23)


@pytest.fixture
def order(event, item, other_item, taxrule):
    testtime = datetime.datetime(2017, 12, 1, 10, 0, 0, tzinfo=UTC)

    with mock.patch('django.utils.timezone.now') as mock_now:
        mock_now.return_value = testtime
        o = Order.objects.create(
            code='FOO', event=event, email='dummy@dummy.test',
            status=Order.STATUS_PAID, secret="k24fiuwvu8kxz3y1",
            datetime=datetime.datetime(2017, 12, 1, 10, 0, 0, tzinfo=UTC),
            expires=datetime.datetime(2017, 12, 10, 10, 0, 0, tzinfo=UTC),
            total=46, locale='en'
        )
        InvoiceAddress.objects.create(order=o, company="Sample company", country=Country('NZ'))
        OrderPosition.objects.create(
            order=o,
            positionid=1,
            item=item,
            variation=None,
            price=Decimal("23"),
            attendee_name_parts={'full_name': "Peter"},
            secret="z3fsn8jyufm5kpk768q69gkbyr5f4h6w",
            pseudonymization_id="ABCDEFGHKL",
        )
        OrderPosition.objects.create(
            order=o,
            positionid=2,
            item=other_item,
            variation=None,
            price=Decimal("23"),
            attendee_name_parts={'full_name': "Michael"},
            secret="sf4HZG73fU6kwddgjg2QOusFbYZwVKpK",
            pseudonymization_id="BACDEFGHKL",
        )
        return o


TEST_ORDERPOSITION1_RES = {
    "id": 1,
    "require_attention": False,
    "order__status": "p",
    "order": "FOO",
    "positionid": 1,
    "item": 1,
    "variation": None,
    "price": "23.00",
    "attendee_name": "Peter",
    "attendee_name_parts": {'full_name': "Peter"},
    "attendee_email": None,
    "voucher": None,
    "tax_rate": "0.00",
    "tax_value": "0.00",
    "tax_rule": None,
    "secret": "z3fsn8jyufm5kpk768q69gkbyr5f4h6w",
    "addon_to": None,
    "checkins": [],
    "downloads": [],
    "answers": [],
    "seat": None,
    "company": None,
    "street": None,
    "zipcode": None,
    "city": None,
    "country": None,
    "state": None,
    "subevent": None,
    "pseudonymization_id": "ABCDEFGHKL",
}

TEST_ORDERPOSITION2_RES = {
    "id": 2,
    "require_attention": False,
    "order__status": "p",
    "order": "FOO",
    "positionid": 2,
    "item": 1,
    "variation": None,
    "price": "23.00",
    "attendee_name": "Michael",
    "attendee_name_parts": {'full_name': "Michael"},
    "attendee_email": None,
    "voucher": None,
    "tax_rate": "0.00",
    "tax_value": "0.00",
    "tax_rule": None,
    "secret": "sf4HZG73fU6kwddgjg2QOusFbYZwVKpK",
    "addon_to": None,
    "checkins": [],
    "downloads": [],
    "answers": [],
    "seat": None,
    "company": None,
    "street": None,
    "zipcode": None,
    "city": None,
    "country": None,
    "state": None,
    "subevent": None,
    "pseudonymization_id": "BACDEFGHKL",
}

TEST_LIST_RES = {
    "name": "Default",
    "all_products": False,
    "limit_products": [],
    "position_count": 0,
    "checkin_count": 0,
    "include_pending": False,
    "allow_multiple_entries": False,
    "allow_entry_after_exit": True,
    "subevent": None,
    "exit_all_at": None,
    "rules": {}
}


@pytest.fixture
def clist(event, item):
    c = event.checkin_lists.create(name="Default", all_products=False)
    c.limit_products.add(item)
    return c


@pytest.fixture
def clist_all(event, item):
    c = event.checkin_lists.create(name="Default", all_products=True)
    return c


@pytest.mark.django_db
def test_list_list(token_client, organizer, event, clist, item, subevent):
    res = dict(TEST_LIST_RES)
    res["id"] = clist.pk
    res["limit_products"] = [item.pk]
    res["auto_checkin_sales_channels"] = []

    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug))
    assert resp.status_code == 200
    assert [res] == resp.data['results']

    clist.subevent = subevent
    clist.save()
    res["subevent"] = subevent.pk
    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/?subevent={}'.format(organizer.slug, event.slug, subevent.pk))
    assert [res] == resp.data['results']
    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/?subevent_match={}'.format(organizer.slug, event.slug, subevent.pk))
    assert [res] == resp.data['results']
    with scopes_disabled():
        se2 = event.subevents.create(name="Foobar", date_from=datetime.datetime(2017, 12, 27, 10, 0, 0, tzinfo=UTC))
    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/?subevent={}'.format(organizer.slug, event.slug, se2.pk))
    assert [] == resp.data['results']
    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/?subevent_match={}'.format(organizer.slug, event.slug, se2.pk))
    assert [] == resp.data['results']

    clist.subevent = None
    clist.save()
    res["subevent"] = None

    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/?subevent_match={}'.format(organizer.slug, event.slug, se2.pk))
    assert [res] == resp.data['results']


@pytest.mark.django_db
def test_list_detail(token_client, organizer, event, clist, item):
    res = dict(TEST_LIST_RES)

    res["id"] = clist.pk
    res["limit_products"] = [item.pk]
    res["auto_checkin_sales_channels"] = []
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/'.format(organizer.slug, event.slug,
                                                                                      clist.pk))
    assert resp.status_code == 200
    assert res == resp.data


@pytest.mark.django_db
def test_list_create(token_client, organizer, event, item, item_on_wrong_event):
    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug),
        {
            "name": "VIP",
            "limit_products": [item.pk],
            "all_products": False,
            "subevent": None,
            "rules": {"==": [0, 1]}
        },
        format='json'
    )
    assert resp.status_code == 201
    with scopes_disabled():
        cl = CheckinList.objects.get(pk=resp.data['id'])
        assert cl.name == "VIP"
        assert cl.limit_products.count() == 1
        assert not cl.all_products
        assert cl.rules == {"==": [0, 1]}

    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug),
        {
            "name": "VIP",
            "limit_products": [item.pk],
            "all_products": False,
            "subevent": None,
            "auto_checkin_sales_channels": [
                "web"
            ]
        },
        format='json'
    )
    assert resp.status_code == 201
    with scopes_disabled():
        cl = CheckinList.objects.get(pk=resp.data['id'])
        assert cl.name == "VIP"
        assert cl.limit_products.count() == 1
        assert not cl.all_products
        assert "web" in cl.auto_checkin_sales_channels

    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug),
        {
            "name": "VIP",
            "limit_products": [item_on_wrong_event.pk],
            "all_products": True,
            "subevent": None
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"non_field_errors":["One or more items do not belong to this event."]}'


@pytest.mark.django_db
def test_list_create_with_subevent(token_client, organizer, event, event3, item, subevent, subevent2):
    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug),
        {
            "name": "VIP",
            "limit_products": [item.pk],
            "all_products": True,
            "subevent": subevent.pk
        },
        format='json'
    )
    assert resp.status_code == 201

    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug),
        {
            "name": "VIP",
            "limit_products": [item.pk],
            "all_products": True,
            "subevent": subevent.pk,
            "auto_checkin_sales_channels": [
                "web"
            ]
        },
        format='json'
    )
    assert resp.status_code == 201
    with scopes_disabled():
        cl = CheckinList.objects.get(pk=resp.data['id'])
        assert "web" in cl.auto_checkin_sales_channels

    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug),
        {
            "name": "VIP",
            "limit_products": [item.pk],
            "all_products": True,
            "subevent": None
        },
        format='json'
    )
    assert resp.status_code == 201

    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event.slug),
        {
            "name": "VIP",
            "limit_products": [],
            "all_products": True,
            "subevent": subevent2.pk
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"non_field_errors":["The subevent does not belong to this event."]}'

    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/checkinlists/'.format(organizer.slug, event3.slug),
        {
            "name": "VIP",
            "limit_products": [],
            "all_products": True,
            "subevent": subevent2.pk
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"non_field_errors":["The subevent does not belong to this event."]}'


@pytest.mark.django_db
def test_list_update(token_client, organizer, event, clist):
    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/checkinlists/{}/'.format(organizer.slug, event.slug, clist.pk),
        {
            "name": "VIP",
        },
        format='json'
    )
    assert resp.status_code == 200
    with scopes_disabled():
        cl = CheckinList.objects.get(pk=resp.data['id'])
    assert cl.name == "VIP"

    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/checkinlists/{}/'.format(organizer.slug, event.slug, clist.pk),
        {
            "auto_checkin_sales_channels": [
                "web"
            ],
        },
        format='json'
    )
    assert resp.status_code == 200
    with scopes_disabled():
        cl = CheckinList.objects.get(pk=resp.data['id'])
        assert "web" in cl.auto_checkin_sales_channels


@pytest.mark.django_db
def test_list_all_items_positions(token_client, organizer, event, clist, clist_all, item, other_item, order):
    with scopes_disabled():
        p1 = dict(TEST_ORDERPOSITION1_RES)
        p1["id"] = order.positions.first().pk
        p1["item"] = item.pk
        p2 = dict(TEST_ORDERPOSITION2_RES)
        p2["id"] = order.positions.last().pk
        p2["item"] = other_item.pk

    # All items
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=positionid'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p1, p2] == resp.data['results']

    # Check-ins on other list ignored
    with scopes_disabled():
        order.positions.first().checkins.create(list=clist)
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=positionid'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p1, p2] == resp.data['results']
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?has_checkin=1'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [] == resp.data['results']

    # Only checked in
    with scopes_disabled():
        c = order.positions.first().checkins.create(list=clist_all)
    p1['checkins'] = [
        {
            'id': c.pk,
            'list': clist_all.pk,
            'datetime': c.datetime.isoformat().replace('+00:00', 'Z'),
            'auto_checked_in': False,
            'device': None,
            'gate': None,
            'type': 'entry',
        }
    ]
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?has_checkin=1'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p1] == resp.data['results']

    # Only not checked in
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?has_checkin=0'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p2] == resp.data['results']

    # Order by checkin
    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=-last_checked_in'.format(
            organizer.slug, event.slug, clist_all.pk
        ))
    assert resp.status_code == 200
    assert [p1, p2] == resp.data['results']
    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=last_checked_in'.format(
            organizer.slug, event.slug, clist_all.pk
        ))
    assert resp.status_code == 200
    assert [p2, p1] == resp.data['results']

    # Order by checkin date
    time.sleep(1)
    with scopes_disabled():
        c = order.positions.last().checkins.create(list=clist_all)
    p2['checkins'] = [
        {
            'id': c.pk,
            'list': clist_all.pk,
            'datetime': c.datetime.isoformat().replace('+00:00', 'Z'),
            'auto_checked_in': False,
            'device': None,
            'gate': None,
            'type': 'entry',
        }
    ]
    resp = token_client.get(
        '/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=-last_checked_in'.format(
            organizer.slug, event.slug, clist_all.pk
        ))
    assert resp.status_code == 200
    assert [p2, p1] == resp.data['results']

    # Order by attendee_name
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=-attendee_name'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p1, p2] == resp.data['results']
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=attendee_name'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p2, p1] == resp.data['results']

    # Paid only
    order.status = Order.STATUS_PENDING
    order.save()
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [] == resp.data['results']

    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ignore_status=true'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    p1['order__status'] = 'n'
    p2['order__status'] = 'n'
    assert [p2, p1] == resp.data['results']


@pytest.mark.django_db
def test_list_all_items_positions_by_subevent(token_client, organizer, event, clist, clist_all, item, other_item, order, subevent):
    with scopes_disabled():
        se2 = event.subevents.create(name="Foobar", date_from=datetime.datetime(2017, 12, 27, 10, 0, 0, tzinfo=UTC))
        pfirst = order.positions.first()
        pfirst.subevent = se2
        pfirst.save()
        p1 = dict(TEST_ORDERPOSITION1_RES)
        p1["id"] = pfirst.pk
        p1["subevent"] = se2.pk
        p1["item"] = item.pk
        plast = order.positions.last()
        plast.subevent = subevent
        plast.save()
        p2 = dict(TEST_ORDERPOSITION2_RES)
        p2["id"] = plast.pk
        p2["item"] = other_item.pk
        p2["subevent"] = subevent.pk
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=positionid'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p1, p2] == resp.data['results']

    clist_all.subevent = subevent
    clist_all.save()
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=positionid'.format(
        organizer.slug, event.slug, clist_all.pk
    ))
    assert resp.status_code == 200
    assert [p2] == resp.data['results']


@pytest.mark.django_db
def test_list_limited_items_positions(token_client, organizer, event, clist, item, order):
    p1 = dict(TEST_ORDERPOSITION1_RES)
    with scopes_disabled():
        p1["id"] = order.positions.first().pk
    p1["item"] = item.pk

    # All items
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/?ordering=positionid'.format(
        organizer.slug, event.slug, clist.pk
    ))
    assert resp.status_code == 200
    assert [p1] == resp.data['results']


@pytest.mark.django_db
def test_list_limited_items_position_detail(token_client, organizer, event, clist, item, order):
    p1 = dict(TEST_ORDERPOSITION1_RES)
    with scopes_disabled():
        p1["id"] = order.positions.first().pk
    p1["item"] = item.pk

    # All items
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/'.format(
        organizer.slug, event.slug, clist.pk, p1["id"]
    ))
    assert resp.status_code == 200
    assert p1 == resp.data


@pytest.mark.django_db
def test_status(token_client, organizer, event, clist_all, item, other_item, order):
    with scopes_disabled():
        op = order.positions.first()
        var1 = item.variations.create(value="XS")
        var2 = item.variations.create(value="S")
        op.variation = var1
        op.save()
        Checkin.objects.create(position=op, list=clist_all)
    resp = token_client.get('/api/v1/organizers/{}/events/{}/checkinlists/{}/status/'.format(
        organizer.slug, event.slug, clist_all.pk,
    ))
    assert resp.status_code == 200
    assert resp.data['checkin_count'] == 1
    assert resp.data['position_count'] == 2
    assert resp.data['inside_count'] == 1
    assert resp.data['items'] == [
        {
            'name': str(item.name),
            'id': item.pk,
            'checkin_count': 1,
            'admission': False,
            'position_count': 1,
            'variations': [
                {
                    'id': var1.pk,
                    'value': 'XS',
                    'checkin_count': 1,
                    'position_count': 1,
                },
                {
                    'id': var2.pk,
                    'value': 'S',
                    'checkin_count': 0,
                    'position_count': 0,
                },
            ]
        },
        {
            'name': other_item.name,
            'id': other_item.pk,
            'checkin_count': 0,
            'admission': False,
            'position_count': 1,
            'variations': []
        }
    ]


@pytest.mark.django_db
def test_custom_datetime(token_client, organizer, clist, event, order):
    dt = now() - datetime.timedelta(days=1)
    dt = dt.replace(microsecond=0)
    with scopes_disabled():
        p = order.positions.first().pk
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p
    ), {
        'datetime': dt.isoformat()
    }, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert Checkin.objects.last().datetime == dt


@pytest.mark.django_db
def test_name_fallback(token_client, organizer, clist, event, order):
    order.invoice_address.name_parts = {'_legacy': 'Paul'}
    order.invoice_address.save()
    with scopes_disabled():
        op = order.positions.first()
    op.attendee_name_cached = None
    op.attendee_name_parts = {}
    op.save()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, op.pk
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    assert resp.data['position']['attendee_name'] == 'Paul'
    assert resp.data['position']['attendee_name_parts'] == {'_legacy': 'Paul'}


@pytest.mark.django_db
def test_by_secret(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.secret
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_by_secret_special_chars(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    p.secret = "abc+-/=="
    p.save()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, urlquote(p.secret, safe='')
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_by_secret_special_chars_space_fallback(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    p.secret = "foo bar"
    p.save()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, "foo+bar"
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_only_once(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'error'
    assert resp.data['reason'] == 'already_redeemed'


@pytest.mark.django_db
def test_reupload_same_nonce(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'nonce': 'foobar'}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'nonce': 'foobar'}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_allow_multiple(token_client, organizer, clist, event, order):
    clist.allow_multiple_entries = True
    clist.save()
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert p.checkins.count() == 2


@pytest.mark.django_db
def test_allow_multiple_reupload_same_nonce(token_client, organizer, clist, event, order):
    clist.allow_multiple_entries = True
    clist.save()
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'nonce': 'foobar'}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'nonce': 'foobar'}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert p.checkins.count() == 1


@pytest.mark.django_db
def test_multiple_different_list(token_client, organizer, clist, clist_all, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'nonce': 'foobar'}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist_all.pk, p.pk
    ), {'nonce': 'baz'}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_forced_multiple(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'force': True}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_forced_flag_set_if_required(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'force': True}, format='json')
    with scopes_disabled():
        assert not p.checkins.order_by('pk').last().forced
        assert p.checkins.order_by('pk').last().force_sent
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'force': True}, format='json')
    with scopes_disabled():
        assert p.checkins.order_by('pk').last().forced
        assert p.checkins.order_by('pk').last().force_sent
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_require_product(token_client, organizer, clist, event, order):
    with scopes_disabled():
        clist.limit_products.clear()
        p = order.positions.first()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'error'
    assert resp.data['reason'] == 'product'


@pytest.mark.django_db
def test_require_paid(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()

    order.status = Order.STATUS_CANCELED
    order.save()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'error'
    assert resp.data['reason'] == 'unpaid'

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'canceled_supported': True}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'error'
    assert resp.data['reason'] == 'canceled'

    order.status = Order.STATUS_PENDING
    order.save()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'error'
    assert resp.data['reason'] == 'unpaid'

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'ignore_unpaid': True}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'error'
    assert resp.data['reason'] == 'unpaid'

    clist.include_pending = True
    clist.save()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'error'
    assert resp.data['reason'] == 'unpaid'

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'ignore_unpaid': True}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.fixture
def question(event, item):
    q = event.questions.create(question=LazyI18nString('Size'), type='C', required=True, ask_during_checkin=True)
    a1 = q.options.create(answer=LazyI18nString("M"))
    a2 = q.options.create(answer=LazyI18nString("L"))
    q.items.add(item)
    return q, a1, a2


@pytest.mark.django_db
def test_question_number(token_client, organizer, clist, event, order, question):
    with scopes_disabled():
        p = order.positions.first()
        question[0].options.all().delete()
    question[0].type = 'N'
    question[0].save()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: "3.24"}}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert order.positions.first().answers.get(question=question[0]).answer == '3.24'


@pytest.mark.django_db
def test_question_choice(token_client, organizer, clist, event, order, question):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: str(question[1].pk)}}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert order.positions.first().answers.get(question=question[0]).answer == 'M'
        assert list(order.positions.first().answers.get(question=question[0]).options.all()) == [question[1]]


@pytest.mark.django_db
def test_question_choice_identifier(token_client, organizer, clist, event, order, question):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: str(question[1].identifier)}}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert order.positions.first().answers.get(question=question[0]).answer == 'M'
        assert list(order.positions.first().answers.get(question=question[0]).options.all()) == [question[1]]


@pytest.mark.django_db
def test_question_invalid(token_client, organizer, clist, event, order, question):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: "A"}}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]


@pytest.mark.django_db
def test_question_required(token_client, organizer, clist, event, order, question):
    with scopes_disabled():
        p = order.positions.first()
    question[0].required = True
    question[0].save()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: ""}}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]


@pytest.mark.django_db
def test_question_optional(token_client, organizer, clist, event, order, question):
    with scopes_disabled():
        p = order.positions.first()
    question[0].required = False
    question[0].save()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: ""}}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'


@pytest.mark.django_db
def test_question_multiple_choice(token_client, organizer, clist, event, order, question):
    with scopes_disabled():
        p = order.positions.first()
    question[0].type = 'M'
    question[0].save()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: "{},{}".format(question[1].pk, question[2].pk)}}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert order.positions.first().answers.get(question=question[0]).answer == 'M, L'
        assert set(order.positions.first().answers.get(question=question[0]).options.all()) == {question[1], question[2]}


@pytest.mark.django_db
def test_question_upload(token_client, organizer, clist, event, order, question):
    r = token_client.post(
        '/api/v1/upload',
        data={
            'media_type': 'image/png',
            'file': ContentFile('file.png', 'invalid png content')
        },
        format='upload',
        HTTP_CONTENT_DISPOSITION='attachment; filename="file.png"',
    )
    assert r.status_code == 201
    file_id_png = r.data['id']

    with scopes_disabled():
        p = order.positions.first()
    question[0].type = 'F'
    question[0].save()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'
    with scopes_disabled():
        assert resp.data['questions'] == [QuestionSerializer(question[0]).data]

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: "invalid"}}, format='json')
    assert resp.status_code == 400
    assert resp.data['status'] == 'incomplete'

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {'answers': {question[0].pk: file_id_png}}, format='json')
    assert resp.status_code == 201
    assert resp.data['status'] == 'ok'
    with scopes_disabled():
        assert order.positions.first().answers.get(question=question[0]).answer.startswith('file://')
        assert order.positions.first().answers.get(question=question[0]).file


@pytest.mark.django_db
def test_store_failed(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/failed_checkins/'.format(
        organizer.slug, event.slug, clist.pk,
    ), {
        'raw_barcode': '123456',
        'error_reason': 'invalid'
    }, format='json')
    assert resp.status_code == 201
    with scopes_disabled():
        assert Checkin.all.filter(successful=False).exists()

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/failed_checkins/'.format(
        organizer.slug, event.slug, clist.pk,
    ), {
        'raw_barcode': '123456',
        'position': p.pk,
        'error_reason': 'unpaid'
    }, format='json')
    assert resp.status_code == 201
    with scopes_disabled():
        assert p.all_checkins.filter(successful=False).count() == 1

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/failed_checkins/'.format(
        organizer.slug, event.slug, clist.pk,
    ), {
        'position': p.pk,
        'error_reason': 'unpaid'
    }, format='json')
    assert resp.status_code == 400

    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/failed_checkins/'.format(
        organizer.slug, event.slug, clist.pk,
    ), {
        'raw_barcode': '123456',
        'error_reason': 'unknown'
    }, format='json')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_redeem_unknown(token_client, organizer, clist, event, order):
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, 'unknown_secret'
    ), {
        'force': True
    }, format='json')
    assert resp.status_code == 404
    assert resp.data["status"] == "error"
    assert resp.data["reason"] == "invalid"
    with scopes_disabled():
        assert not Checkin.objects.last()


@pytest.mark.django_db
def test_redeem_unknown_revoked(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
        event.revoked_secrets.create(position=p, secret='revoked_secret')
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, 'revoked_secret'
    ), {
    }, format='json')
    assert resp.status_code == 400
    assert resp.data["status"] == "error"
    assert resp.data["reason"] == "revoked"
    with scopes_disabled():
        assert not Checkin.objects.last()


@pytest.mark.django_db
def test_redeem_unknown_revoked_force(token_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
        event.revoked_secrets.create(position=p, secret='revoked_secret')
    resp = token_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, 'revoked_secret'
    ), {
        'force': True
    }, format='json')
    assert resp.status_code == 201
    assert resp.data["status"] == "ok"
    with scopes_disabled():
        assert Checkin.objects.last().forced
        assert Checkin.objects.last().force_sent


@pytest.mark.django_db
def test_redeem_unknown_legacy_device_bug(device, device_client, organizer, clist, event, order):
    device.software_brand = "pretixSCAN"
    device.software_version = "1.11.1"
    device.save()
    resp = device_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, 'unknown_secret'
    ), {
        'force': True
    }, format='json')
    assert resp.status_code == 400
    assert resp.data["status"] == "error"
    assert resp.data["reason"] == "already_redeemed"
    with scopes_disabled():
        assert not Checkin.objects.last()

    device.software_brand = "pretixSCAN"
    device.software_version = "1.11.2"
    device.save()
    resp = device_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, 'unknown_secret'
    ), {
        'force': True
    }, format='json')
    assert resp.status_code == 404
    assert resp.data["status"] == "error"
    assert resp.data["reason"] == "invalid"
    with scopes_disabled():
        assert not Checkin.objects.last()


@pytest.mark.django_db
def test_redeem_by_id_not_allowed_if_pretixscan(device, device_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    device.software_brand = "pretixSCAN"
    device.software_version = "1.14.2"
    device.save()
    resp = device_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {
        'force': True
    }, format='json')
    print(resp.data)
    assert resp.status_code == 404
    resp = device_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/'.format(
        organizer.slug, event.slug, clist.pk, p.secret
    ), {
        'force': True
    }, format='json')
    assert resp.status_code == 201


@pytest.mark.django_db
def test_redeem_by_id_not_allowed_if_untrusted(device, device_client, organizer, clist, event, order):
    with scopes_disabled():
        p = order.positions.first()
    resp = device_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/?untrusted_input=true'.format(
        organizer.slug, event.slug, clist.pk, p.pk
    ), {
        'force': True
    }, format='json')
    assert resp.status_code == 404
    resp = device_client.post('/api/v1/organizers/{}/events/{}/checkinlists/{}/positions/{}/redeem/?untrusted_input=true'.format(
        organizer.slug, event.slug, clist.pk, p.secret
    ), {
        'force': True
    }, format='json')
    assert resp.status_code == 201