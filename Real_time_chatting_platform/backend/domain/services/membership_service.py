from __future__ import annotations

from domain.entities.conversation_member import Role
from domain.exceptions import InsufficientPermissionError


class MembershipService:
    """Pure rules for who can do what to whom within a group's membership.

    These rules only look at roles. Rules that need to see the whole member
    list (e.g. "don't remove the last owner") live in the use cases, which are
    the layer that can actually load that list.
    """

    @staticmethod
    def can_change_role(actor_role: Role, target_role: Role, new_role: Role) -> bool:
        # Only an owner may grant or revoke ownership.
        if new_role == "owner" or target_role == "owner":
            return actor_role == "owner"
        # Owners can set any non-owner role on any non-owner member.
        if actor_role == "owner":
            return True
        # Admins can only move plain members between member <-> admin;
        # they cannot touch other admins or owners.
        if actor_role == "admin":
            return target_role == "member"
        return False

    @staticmethod
    def can_remove_member(actor_role: Role, target_role: Role) -> bool:
        # Nobody can remove an owner — an owner leaves under their own steam.
        if target_role == "owner":
            return False
        # Owners can remove anyone else; admins cannot remove other admins.
        if actor_role == "owner":
            return True
        if actor_role == "admin":
            return target_role == "member"
        return False

    @staticmethod
    def can_add_member(actor_role: Role) -> bool:
        # Owners and admins may invite; plain members may not. Only the actor's
        # role matters — unlike the rules above there is no target role yet,
        # because the person being added is not in the conversation.
        return actor_role in ("owner", "admin")

    @staticmethod
    def assert_can_add_member(actor_role: Role) -> None:
        if not MembershipService.can_add_member(actor_role):
            raise InsufficientPermissionError("Only owners and admins can add members")

    @staticmethod
    def assert_can_change_role(actor_role: Role, target_role: Role, new_role: Role) -> None:
        if not MembershipService.can_change_role(actor_role, target_role, new_role):
            raise InsufficientPermissionError("You do not have permission to change this member's role")

    @staticmethod
    def assert_can_remove_member(actor_role: Role, target_role: Role) -> None:
        if not MembershipService.can_remove_member(actor_role, target_role):
            raise InsufficientPermissionError("You do not have permission to remove this member")
