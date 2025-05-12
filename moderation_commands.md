# Moderation Commands

## Basic Moderation
- `ban <member> <delete_history> <reason>` - Bans the mentioned user
- `kick <member> <reason>` - Kicks the mentioned user
- `unban <user_id> <reason>` - Unbans the user with the given ID
- `timeout <member> <duration> <reason>` - Mutes the provided member using Discord's timeout feature
- `untimeout <member> <reason>` - Removes a timeout from a member
- `softban <member> <reason>` - Softbans the mentioned user and deleting 1 day of messages
- `purge <amount> <member>` - Deletes the specified amount of messages from the current channel

## Advanced Moderation
- `hardban <user_id> <reason>` - Keep a member banned
- `hardban_list` - View list of hardbanned members
- `clearinvites` - Remove all existing invites in guild
- `drag <members> <channel>` - Drag member(s) to the specified Voice Channel
- `unbanall` - Unbans every member in a guild
- `unbanall_cancel` - Cancels a unban all task running
- `temprole <member> <duration> <role>` - Temporarily give a role to a member
- `temprole_list` - List all active temporary roles

## Purge Commands
- `purge <amount> <member>` - Deletes the specified amount of messages from the current channel
- `purge startswith <substring>` - Purge messages that start with a given substring
- `purge stickers <search>` - Purge stickers from chat
- `purge mentions <member> <search>` - Purge mentions for a member from chat
- `purge after <message>` - Purge messages after a given message ID
- `purge bots <search>` - Purge messages from bots in chat
- `purge humans <search>` - Purge messages from humans in chat
- `purge contains <substring>` - Purges messages containing given substring
- `purge emoji <search>` - Purge emojis from chat
- `purge links <search>` - Purge messages containing links
- `purge reactions <search>` - Purge reactions from messages in chat
- `purge webhooks <search>` - Purge messages from webhooks in chat
- `purge upto <message>` - Purge messages up to a message link
- `purge attachments <search>` - Purge files/attachments from chat
- `purge between <start> <finish>` - Purge between two messages
- `purge embeds <search>` - Purge embeds from chat
- `purge before <message>` - Purge messages before a given message ID
- `purge endswith <substring>` - Purge messages that ends with a given substring
- `purge images <search>` - Purge images (including links) from chat
- `botclear <search>` - Clear messages from bots (alias for purge bots)

## Channel Management
- `lockdown <channel> <reason>` - Prevent regular members from typing
- `lockdown_ignore` - Prevent channels from being altered during lockdown all
- `lockdown_ignore add <channel>` - Add a channel to the ignore list
- `lockdown_ignore remove <channel>` - Remove a channel from the ignore list
- `lockdown_ignore list` - List all ignored channels
- `lockdown_all <reason>` - Prevent regular members from typing in all channels
- `unlockdown <channel> <reason>` - Allow regular members to type
- `unlockdown_all <reason>` - Allow regular members to type in all channels
- `hide <channel> <target>` - Hide a channel from a role or member
- `unhide <channel> <target>` - Unhide a channel from a role or member
- `nuke` - Clone the current channel

## Kick.com Commands
- `kick` - Group of Kick.com commands for stream notifications
- `kick add <channel> <username>` - Add stream notifications to channel
- `kick remove <channel> <username>` - Remove stream notifications from a channel
- `kick list` - View all Kick stream notifications
- `kick message <username> <message>` - Set a message for Kick notifications
- `kick message_view <username>` - View Kick message for new streams 