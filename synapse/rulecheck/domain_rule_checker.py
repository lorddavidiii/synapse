# -*- coding: utf-8 -*-
# Copyright 2018 New Vector Ltd
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

import logging

from synapse.config._base import ConfigError

logger = logging.getLogger(__name__)


class DomainRuleChecker(object):
    """
    A re-implementation of the SpamChecker that prevents users in one domain from
    inviting users in other domains to rooms, based on a configuration.

    Takes a config in the format:

    spam_checker:
        module: "rulecheck.DomainRuleChecker"
        config:
          domain_mapping:
            "inviter_domain": [ "invitee_domain_permitted", "other_domain_permitted" ]
            "other_inviter_domain": [ "invitee_domain_permitted" ]
          default: False

          # Only let local users join rooms if they were explicitly invited.
          can_only_join_rooms_with_invite: false

          # Only let local users create rooms if they are inviting only one
          # other user, and that user matches the rules above.
          can_only_create_one_to_one_rooms: false

          # Only let local users invite during room creation, regardless of the
          # domain mapping rules above.
          can_only_invite_during_room_creation: false

    Don't forget to consider if you can invite users from your own domain.
    """

    def __init__(self, config):
        self.domain_mapping = config["domain_mapping"] or {}
        self.default = config["default"]

        self.can_only_join_rooms_with_invite = config.get(
            "can_only_join_rooms_with_invite", False,
        )
        self.can_only_create_one_to_one_rooms = config.get(
            "can_only_create_one_to_one_rooms", False,
        )
        self.can_only_invite_during_room_creation = config.get(
            "can_only_invite_during_room_creation", False,
        )

    def check_event_for_spam(self, event):
        """Implements synapse.events.SpamChecker.check_event_for_spam
        """
        return False

    def user_may_invite(self, inviter_userid, invitee_userid, room_id,
                        new_room):
        """Implements synapse.events.SpamChecker.user_may_invite
        """
        if self.can_only_invite_during_room_creation and not new_room:
            return False

        inviter_domain = self._get_domain_from_id(inviter_userid)
        invitee_domain = self._get_domain_from_id(invitee_userid)

        if inviter_domain not in self.domain_mapping:
            return self.default

        return invitee_domain in self.domain_mapping[inviter_domain]

    def user_may_create_room(self, userid, invite_list, cloning):
        """Implements synapse.events.SpamChecker.user_may_create_room
        """

        if cloning:
            return True

        if self.can_only_create_one_to_one_rooms and len(invite_list) != 1:
            return False

        return True

    def user_may_create_room_alias(self, userid, room_alias):
        """Implements synapse.events.SpamChecker.user_may_create_room_alias
        """
        return True

    def user_may_publish_room(self, userid, room_id):
        """Implements synapse.events.SpamChecker.user_may_publish_room
        """
        return True

    def user_may_join_room(self, userid, room_id, is_invited):
        """Implements synapse.events.SpamChecker.user_may_join_room
        """
        if self.can_only_join_rooms_with_invite and not is_invited:
            return False

        return True

    @staticmethod
    def parse_config(config):
        """Implements synapse.events.SpamChecker.parse_config
        """
        if "default" in config:
            return config
        else:
            raise ConfigError("No default set for spam_config DomainRuleChecker")

    @staticmethod
    def _get_domain_from_id(mxid):
        """Parses a string and returns the domain part of the mxid.

        Args:
           mxid (str): a valid mxid

        Returns:
           str: the domain part of the mxid

        """
        idx = mxid.find(":")
        if idx == -1:
            raise Exception("Invalid ID: %r" % (mxid,))
        return mxid[idx + 1:]
