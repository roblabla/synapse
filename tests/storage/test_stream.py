# -*- coding: utf-8 -*-
# Copyright 2014 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from tests import unittest
from twisted.internet import defer

from synapse.api.constants import EventTypes, Membership
from synapse.types import UserID, RoomID
from tests.storage.event_injector import EventInjector

from tests.utils import setup_test_homeserver

from mock import Mock


class StreamStoreTestCase(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):
        hs = yield setup_test_homeserver(
            resource_for_federation=Mock(),
            http_client=None,
        )

        self.store = hs.get_datastore()
        self.event_builder_factory = hs.get_event_builder_factory()
        self.event_injector = EventInjector(hs)
        self.handlers = hs.get_handlers()
        self.message_handler = self.handlers.message_handler

        self.u_alice = UserID.from_string("@alice:test")
        self.u_bob = UserID.from_string("@bob:test")

        self.room1 = RoomID.from_string("!abc123:test")
        self.room2 = RoomID.from_string("!xyx987:test")

    @defer.inlineCallbacks
    def test_event_stream_get_other(self):
        # Both bob and alice joins the room
        yield self.event_injector.inject_room_member(
            self.room1, self.u_alice, Membership.JOIN
        )
        yield self.event_injector.inject_room_member(
            self.room1, self.u_bob, Membership.JOIN
        )

        # Initial stream key:
        start = yield self.store.get_room_events_max_id()

        yield self.event_injector.inject_message(self.room1, self.u_alice, u"test")

        end = yield self.store.get_room_events_max_id()

        results, _ = yield self.store.get_room_events_stream(
            self.u_bob.to_string(),
            start,
            end,
        )

        self.assertEqual(1, len(results))

        event = results[0]

        self.assertObjectHasAttributes(
            {
                "type": EventTypes.Message,
                "user_id": self.u_alice.to_string(),
                "content": {"body": "test", "msgtype": "message"},
            },
            event,
        )

    @defer.inlineCallbacks
    def test_event_stream_get_own(self):
        # Both bob and alice joins the room
        yield self.event_injector.inject_room_member(
            self.room1, self.u_alice, Membership.JOIN
        )
        yield self.event_injector.inject_room_member(
            self.room1, self.u_bob, Membership.JOIN
        )

        # Initial stream key:
        start = yield self.store.get_room_events_max_id()

        yield self.event_injector.inject_message(self.room1, self.u_alice, u"test")

        end = yield self.store.get_room_events_max_id()

        results, _ = yield self.store.get_room_events_stream(
            self.u_alice.to_string(),
            start,
            end,
        )

        self.assertEqual(1, len(results))

        event = results[0]

        self.assertObjectHasAttributes(
            {
                "type": EventTypes.Message,
                "user_id": self.u_alice.to_string(),
                "content": {"body": "test", "msgtype": "message"},
            },
            event,
        )

    @defer.inlineCallbacks
    def test_event_stream_join_leave(self):
        # Both bob and alice joins the room
        yield self.event_injector.inject_room_member(
            self.room1, self.u_alice, Membership.JOIN
        )
        yield self.event_injector.inject_room_member(
            self.room1, self.u_bob, Membership.JOIN
        )

        # Then bob leaves again.
        yield self.event_injector.inject_room_member(
            self.room1, self.u_bob, Membership.LEAVE
        )

        # Initial stream key:
        start = yield self.store.get_room_events_max_id()

        yield self.event_injector.inject_message(self.room1, self.u_alice, u"test")

        end = yield self.store.get_room_events_max_id()

        results, _ = yield self.store.get_room_events_stream(
            self.u_bob.to_string(),
            start,
            end,
        )

        # We should not get the message, as it happened *after* bob left.
        self.assertEqual(0, len(results))

    @defer.inlineCallbacks
    def test_event_stream_prev_content(self):
        yield self.event_injector.inject_room_member(
            self.room1, self.u_bob, Membership.JOIN
        )

        event1 = yield self.event_injector.inject_room_member(
            self.room1, self.u_alice, Membership.JOIN
        )

        start = yield self.store.get_room_events_max_id()

        event2 = yield self.event_injector.inject_room_member(
            self.room1, self.u_alice, Membership.JOIN,
        )

        end = yield self.store.get_room_events_max_id()

        results, _ = yield self.store.get_room_events_stream(
            self.u_bob.to_string(),
            start,
            end,
        )

        # We should not get the message, as it happened *after* bob left.
        self.assertEqual(1, len(results))

        event = results[0]

        self.assertTrue(
            "prev_content" in event.unsigned,
            msg="No prev_content key"
        )
