# QxrK Discord Bot

A feature-rich Discord bot with moderation, reaction, utility, economy, and LastFM features.

## Features

- **Moderation Commands**: Ban, kick, timeout, purge messages, and more
- **Kick.com Integration**: Stream notifications and management
- **Reaction Commands**: Express emotions with GIFs and set up automatic reactions to messages and keywords
- **Utility Commands**: Server info, user info, avatar display, and other utilities
- **BumpReminder**: Get reminders to /bump your server on Disboard
- **Economy System**: Virtual currency, gambling, shop, and inventory management
- **Music Features**: Queue tracks, manage the queue, and adjust volume
- **LastFM Integration**: Track scrobbles, view now playing, and compare music tastes
- **Starboard**: Showcase the best messages from your server based on reactions
- **ClownBoard**: Showcase the worst messages from your server based on reactions
- **Snipe**: Retrieve deleted and edited messages, track reactions in your server
- **Crypto**: Check cryptocurrency prices and monitor blockchain transactions
- **AutoRole**: Automatic role assignment when members join and self-assignable roles
- **AntiRaid**: Protection against mass raids with features like new account detection
- **AntiNuke**: Protection against server nuking with mass action prevention
- **Counters**: Track member count and booster count in channel names
- **AutoPfp**: Automatic profile picture and banner channels with customizable categories
- **Servers**: Pin archival, image-only channels, fake permissions, and message filters
- **Roleplay**: Express emotions and actions through interactive commands with anime GIFs
- **Spotify Integration**: Control your Spotify playback and view music information directly in Discord
- **SoundCloud Integration**: Search for tracks and set up notifications for new uploads from artists
- **YouTube Integration**: Repost YouTube videos and set up notifications for new uploads
- **Twitch Integration**: View channel information and set up notifications for streams
- **X Integration**: Lookup X users and get notifications for new posts
- **TikTok Integration**: Lookup TikTok users and get notifications for new videos
- **Instagram Integration**: Lookup Instagram users and get notifications for new posts
- **Ticket System**: Create and manage support tickets with customizable categories and topics

## Setup

1. **Clone this repository**:
   ```
   git clone https://github.com/yourusername/qxrkbot.git
   cd qxrkbot
   ```

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Create a `.env` file** with the following variables:
   ```
   TOKEN=your_discord_bot_token
   PREFIX=!
   LASTFM_API_KEY=your_lastfm_api_key
   LASTFM_API_SECRET=your_lastfm_api_secret
   ```

4. **Run the bot**:
   ```
   python bot.py
   ```

## Command Categories

### Moderation
- `ban <member> <delete_history> <reason>`: Bans the mentioned user
- `ban purge <delete_history>`: Set default ability to delete message history upon ban
- `unban <user_id> <reason>`: Unbans the user with the given ID
- `tempban <member> <duration> <reason>`: Temporarily ban members
- `kick <member> <reason>`: Kicks the mentioned user from the server
- `timeout <member> <duration> <reason>`: Mutes the provided member using Discord's timeout feature
- `timeout list`: View list of timed out members
- `untimeout <member> <reason>`: Removes a timeout from a member
- `untimeout all`: Untimeout all timed out members
- `softban <member> <reason>`: Softbans the mentioned user and deleting 1 day of messages
- `hardban <user_id> <reason>`: Keeps a member permanently banned (auto-rebans)
- `hardban_list`: View list of hardbanned members
- `bans`: View a list of the banned members
- `moderationhistory <member> <command>`: View moderation actions from a staff member
- `clearinvites`: Remove all existing invites in the guild
- `drag <members> <channel>`: Drag member(s) to the specified Voice Channel
- `unbanall`: Unbans every member in the guild
- `unbanall_cancel`: Cancels a running unban all task
- `temprole <member> <duration> <role>`: Temporarily give a role to a member
- `temprole_list`: List all active temporary roles
- `jail <member> <duration> <reason>`: Jails the mentioned user
- `jaillist`: View a list of every current jailed member
- `unjail <member>`: Unjails the mentioned user
- `stfu <user>`: Toggle deletion of a user's messages anytime they send one
- `newusers <count>`: View list of recently joined members
- `notes <member>`: View notes on a member
- `notes add <member> <note>`: Add a note for a member
- `notes remove <member> <id>`: Removes a note for a member
- `notes clear <member>`: Clears all notes for a member

#### Role Management
- `role <member> <roles>`: Modify a member's roles
- `role create <name> <color>`: Creates a role with optional color
- `role delete <role>`: Deletes a role
- `role edit <role> <name>`: Change a role name
- `role color <role> <color>`: Changes a role's color
- `role icon <role> <icon>`: Set an icon for a role
- `role add <member> <role>`: Adds role to a member
- `role remove <member> <role>`: Removes role from a member
- `role restore <member>`: Restore roles to a member
- `role hoist <role>`: Toggle hoisting a role
- `role mentionable <role>`: Toggle mentioning a role
- `role has <assigned> <role>`: Add a role to members with a specific role
- `role has remove <role>`: Remove a role from members with a specific role
- `role has cancel`: Cancel a role all task
- `role all bots <role>`: Gives a role to all bots
- `role all bots remove <role>`: Remove a role from all bots
- `role all humans <role>`: Gives a role to all non-bots
- `role all humans remove <role>`: Remove a role from all humans
- `role all cancel`: Cancel a role all task
- `stickyrole add <member> <role>`: Reapplies a role on join
- `stickyrole remove <member> <role>`: Removes a setup sticky role
- `stickyrole list`: View a list of every sticky role

#### Purge Commands
- `purge <amount> <member>`: Deletes the specified amount of messages from the current channel
- `purge startswith <substring>`: Purge messages that start with a given substring
- `purge stickers <search>`: Purge stickers from chat
- `purge mentions <member> <search>`: Purge mentions for a member from chat
- `purge after <message>`: Purge messages after a given message ID
- `purge bots <search>`: Purge messages from bots in chat
- `purge humans <search>`: Purge messages from humans in chat
- `purge contains <substring>`: Purges messages containing given substring
- `purge emoji <search>`: Purge emojis from chat
- `purge links <search>`: Purge messages containing links
- `purge reactions <search>`: Purge reactions from messages in chat
- `purge webhooks <search>`: Purge messages from webhooks in chat
- `purge upto <message>`: Purge messages up to a message link
- `purge attachments <search>`: Purge files/attachments from chat
- `purge between <start> <finish>`: Purge between two messages
- `purge embeds <search>`: Purge embeds from chat
- `purge before <message>`: Purge messages before a given message ID
- `purge endswith <substring>`: Purge messages that end with a given substring
- `purge images <search>`: Purge images (including links) from chat
- `botclear <search>`: Clear messages from bots (alias for purge bots)

#### Channel Management
- `lockdown <channel> <reason>`: Prevent regular members from typing
- `lockdown_ignore`: Prevent channels from being altered during lockdown all
- `lockdown_ignore add <channel>`: Add a channel to the ignore list
- `lockdown_ignore remove <channel>`: Remove a channel from the ignore list
- `lockdown_ignore list`: List all ignored channels
- `lockdown_all <reason>`: Prevent regular members from typing in all channels
- `unlockdown <channel> <reason>`: Allow regular members to type
- `unlockdown_all <reason>`: Allow regular members to type in all channels
- `hide <channel> <target>`: Hide a channel from a role or member
- `unhide <channel> <target>`: Unhide a channel from a role or member
- `nuke`: Clone the current channel and delete the original
- `nuke add <channel> <interval> <message>`: Schedule nuke for a channel
- `nuke remove <channel>`: Remove scheduled nuke for a channel
- `nuke list`: View all scheduled nukes
- `slowmode on <channel> <delay>`: Enable slowmode in a channel
- `slowmode off <channel>`: Disables slowmode in a channel
- `revokefiles on <channel>`: Enable permissions to attach files & embed links in a channel
- `revokefiles off <channel>`: Disables permissions to attach files & embed links in a channel
- `talk <channel> <role>`: Toggle a channel to text for a role
- `topic <text>`: Change the current channel topic
- `thread lock <thread> <reason>`: Lock a thread or forum post
- `thread unlock <thread> <reason>`: Unlock a thread or forum post

#### Member Restrictions
- `imute <member> <reason>`: Remove a member's attach files & embed links permission
- `iunmute <member> <reason>`: Restores a member's attach files & embed links permission
- `rmute <member> <reason>`: Remove a member's add reactions & use external emotes permission
- `runmute <member> <reason>`: Restores a member's add reactions & use external emotes permission
- `forcenickname <member> <name>`: Force a member's current nickname
- `forcenickname list`: View a list of all forced nicknames

#### Raid Protection
- `raid <time> <action> <reason>`: Remove all members that joined in the time provided in the event of a raid
- `raid cancel`: End a chunkban of raid members
- `recentban <count> <reason>`: Chunk ban recently joined members
- `recentban cancel`: Stop a chunk banning task

#### Command Restrictions
- `restrictcommand add <cmd> <role>`: Allows the specified role exclusive permission to use a command
- `restrictcommand remove <cmd> <role>`: Removes the specified role's exclusive permission to use a command
- `restrictcommand list`: View a list of every restricted command
- `restrictcommand reset`: Removes every restricted command

#### Reminders
- `remind <timeframe> <reason>`: Get reminders for a duration set about whatever you choose
- `remind remove <id>`: Remove a reminder
- `remind list`: View a list of your reminders
- `reminders`: View a list of your reminders

### Kick.com Integration
- `setstream`: Set up stream notifications for a Kick.com channel
- `delstream`: Remove stream notifications
- `kick add <channel> <username>`: Add stream notifications to channel
- `kick remove <channel> <username>`: Remove stream notifications from a channel
- `kick list`: View all Kick stream notifications
- `kick message <username> <message>`: Set a message for Kick notifications
- `kick message view <username>`: View Kick message for new streams

### YouTube Integration
- `staryoutube <url>`: Repost a YouTube video
- `staryoutube add <user> <channel>`: Add YouTube user to feed posts into a channel
- `staryoutube remove <username> <channel>`: Remove a user from a channel's YouTube feed
- `staryoutube list`: List YouTube feed channels
- `staryoutube clear`: Reset all YouTube feeds that have been setup

### Twitch Integration
- `twitch <username>`: Lookup a Twitch channel
- `twitch add <username> <channel>`: Add Twitch notifications to a channel
- `twitch remove <username> <channel>`: Remove Twitch notifications from a channel
- `twitch list`: List all Twitch notifications
- `twitch clear`: Reset all Twitch notifications
- `twitch message <username> <message>`: Set a custom message for stream notifications

### X Integration
- `x <username>`: Lookup an X user and view recent posts
- `x add <username> <channel>`: Add X user to feed posts into a channel
- `x remove <username> <channel>`: Remove a user from a channel's X feed
- `x list`: List X feed channels
- `x clear`: Reset all X feeds that have been setup

### TikTok Integration
- `tiktok <username>`: Lookup a TikTok user or feed their posts into a channel
- `startiktok add <username> <channel>`: Add a TikTok user to have their posts feeded into a channel
- `startiktok remove <username> <channel>`: Remove a user from a channel's TikTok feed
- `startiktok list`: List TikTok feed channels
- `startiktok clear`: Reset all TikTok feeds that have been setup

### Instagram Integration
- `instagram <username>`: Lookup an Instagram user or follow their timeline
- `starinstagram add <username> <channel>`: Add an Instagram user to have their posts feeded into a channel
- `starinstagram remove <username> <channel>`: Remove a user from a channel's Instagram feed
- `starinstagram list`: List Instagram feed channels
- `starinstagram clear`: Reset all Instagram feeds that have been setup

### Ticket System
- `ticket`: Make a ticket panel for your guild
- `ticket topics`: Manage the ticket topics
- `ticket topics add <topic>`: Add a new ticket topic
- `ticket topics remove <topic>`: Remove a ticket topic
- `ticket topics clear`: Remove all ticket topics
- `ticket add <member>`: Add a person to the ticket
- `ticket remove <member>`: Remove a member from the ticket
- `ticket rename <name>`: Rename a ticket channel
- `ticket close`: Close the ticket
- `ticket opened <code>`: Set a message to be sent when a member opens a ticket
- `ticket reset`: Disable the ticket module in the server
- `ticket support <role>`: Configure the ticket support role
- `ticket send <channel> [code]`: Send the ticket panel to a channel
- `ticket emojis`: Edit the ticket emojis
- `ticket emojis open <emoji>`: Set the emoji to open the ticket
- `ticket emojis close <emoji>`: Set the emoji to close the ticket
- `ticket category <category>`: Configure the category where the tickets should open
- `ticket config`: Check the server's ticket settings
- `ticket logs <channel>`: Configure a channel for logging ticket transcripts

### Reactions
- `hug`: Send a hug GIF to someone
- `kiss`: Send a kiss GIF to someone
- `surprised`: Show a surprised reaction
- `add_reaction <message_id> <emoji>`: Add a reaction(s) to a message (alternative command)
- `reaction <message_id> <emoji>`: Add a reaction(s) to a message
- `reaction add <emoji> <trigger>`: Add a reaction trigger to guild
- `reaction delete <emoji> <trigger>`: Remove a reaction trigger from guild
- `reaction list`: View all reaction triggers in the guild
- `reaction clear`: Remove all reaction triggers in the guild
- `reaction deleteall <trigger>`: Remove all reaction triggers for a specific word
- `reaction owner <trigger>`: View who created a specific trigger
- `reaction messages <channel> <emoji1> [emoji2] [emoji3]`: Set auto reactions for a channel
- `reaction messages_list`: List all auto reactions for channels

### Utility
- `serverinfo`: Display information about the server
- `userinfo`: Display information about a user
- `avatar`: Show a user's avatar
- `help`: Display help for commands

### BumpReminder
- `bumpreminder`: Get reminders to /bump your server on Disboard
- `bumpreminder channel`: Set Bump Reminder channel for the server
- `bumpreminder message`: Set the reminder message to run /bump
- `bumpreminder thankyou`: Set the 'Thank You' message for successfully running /bump
- `bumpreminder autoclean`: Automatically delete messages that aren't /bump
- `bumpreminder autolock`: Lock channel until ready to use /bump
- `bumpreminder config`: View server configuration for Bump Reminder

### Economy
- `balance`: Check your currency balance
- `daily`: Claim daily rewards
- `gamble`: Try your luck to win more currency
- `shop`: Browse the item shop
- `inventory`: View your inventory
- `transfer`: Send currency to another user

### Levels
- `levels`: View your level or setup the leveling system
- `levels leaderboard`: View the highest ranking members
- `levels roles`: Show all level rewards
- `levels add`: Create level role rewards
- `levels remove`: Remove a level role
- `levels ignore`: Ignore a channel or role for XP
- `levels reset`: Reset all levels and configurations
- `levels message`: Set a message for leveling up
- `setlevel`: Set a user's level
- `setxp`: Set a user's experience
- `removexp`: Remove experience from a user

### Music
- `play`: Queue a track
- `queue`: View all tracks queued
- `queue remove`: Remove a track from the queue
- `queue move`: Move a track in the queue
- `queue shuffle`: Shuffle the music queue
- `skip`: Skip the current track
- `current`: View the current track
- `pause`: Pause the track
- `resume`: Resume the track
- `volume`: Adjust the track volume
- `clear`: Clear the queue
- `disconnect`: Disconnect the player
- `repeat`: Change the current loop mode
- `fastforward`: Fast forward to a specific position
- `rewind`: Rewind to a specific position

#### Sound Presets
- `preset`: Use a preset for Music
- `preset chipmunk`: High-pitched, chipmunk-like sound
- `preset flat`: Normal EQ setting with default levels
- `preset boost`: Enhanced bass and highs for energetic feel
- `preset 8d`: Stereo-like panning effect for immersive sound
- `preset active`: List all currently applied filters
- `preset vibrato`: Wavering pitch effect for dynamic tone
- `preset vaporwave`: Slowed playback for nostalgic half-speed effect
- `preset metal`: Amplified midrange for concert-like sound
- `preset karaoke`: Filters out vocals leaving only instrumental
- `preset nightcore`: Accelerated playback for nightcore-style music
- `preset piano`: Enhanced mid and high tones for piano tracks
- `preset soft`: Cuts high and mid frequencies, allowing only low frequencies

### LastFM
- `lastfm nowplaying`: Show current or last played track
- `lastfm recent`: View recently played tracks
- `lastfm login`: Link your LastFM account
- `lastfm topartists`: View your top artists
- `lastfm topalbums`: View your top albums
- `lastfm toptracks`: View your top tracks
- `lastfm taste`: Compare music tastes with another user
- `lastfm whoknows`: See who listens to an artist in the server

### Starboard
- `starboard set`: Set the channel for the starboard and (optionally) its emoji
- `starboard threshold`: Sets the number of reactions needed for a message to be posted
- `starboard emoji`: Sets the emoji that triggers starboard messages
- `starboard ignore`: Ignore a channel, member, or role for starboard reactions
- `starboard ignore_list`: View ignored roles, members and channels for Starboard
- `starboard settings`: Display your current starboard settings
- `starboard selfstar`: Allow or disallow authors to star their own messages
- `starboard lock`: Disables/locks starboard from operating
- `starboard unlock`: Enables/unlocks starboard from operating
- `starboard jumpurl`: Allow or disallow the jump URL to appear on starboard posts
- `starboard attachments`: Allow or disallow attachments to appear on starboard posts
- `starboard timestamp`: Allow or disallow timestamps to appear on starboard posts
- `starboard color`: Set the starboard embed color
- `starboard reset`: Reset the guild's starboard configuration

### ClownBoard
- `clownboard set`: Set the channel for the clownboard and (optionally) its emoji
- `clownboard threshold`: Sets the number of reactions needed for a message to be posted
- `clownboard emoji`: Sets the emoji that triggers clownboard messages
- `clownboard ignore`: Ignore a channel, member, or role for clownboard reactions
- `clownboard ignore_list`: View ignored roles, members and channels for ClownBoard
- `clownboard settings`: Display your current clownboard settings
- `clownboard selfstar`: Allow or disallow authors to react to their own messages
- `clownboard lock`: Disables/locks clownboard from operating
- `clownboard unlock`: Enables/unlocks clownboard from operating
- `clownboard jumpurl`: Allow or disallow the jump URL to appear on clownboard posts
- `clownboard attachments`: Allow or disallow attachments to appear on clownboard posts
- `clownboard timestamp`: Allow or disallow timestamps to appear on clownboard posts
- `clownboard color`: Set the clownboard embed color
- `clownboard reset`: Reset the guild's clownboard configuration

### AutoRole
- `buttonrole`: No description provided
- `buttonrole list`: View a list of every button role
- `buttonrole remove`: Remove a button role from a message
- `buttonrole reset`: Clears every button role from guild
- `buttonrole removeall`: Removes all button roles from a message
- `reactionrole`: Set up self-assignable roles with reactions
- `reactionrole list`: View a list of every reaction role
- `reactionrole remove`: Removes a reaction role from a message
- `reactionrole removeall`: Removes all reaction roles from a message
- `reactionrole reset`: Clears every reaction role from guild
- `reactionrole add`: Adds a reaction role to a message
- `autorole`: Set up automatic role assign on member join
- `autorole reset`: Clears every autorole for guild
- `autorole add`: Adds a autorole and assigns on join to member
- `autorole remove`: Removes a autorole and stops assigning on join
- `autorole list`: View a list of every auto role

### AntiRaid
- `antiraid`: Configure protection against potential raids
- `antiraid newaccounts`: Punish new registered accounts
- `antiraid massjoin`: Protect server against mass bot raids 
- `antiraid avatar`: Punish accounts without a profile picture
- `antiraid config`: View server antiraid configuration
- `antiraid state`: Turn off server's raid state
- `antiraid whitelist`: Create a one-time whitelist to allow a user to join
- `antiraid whitelist view`: View all current antinuke whitelists

### AntiNuke
- `antinuke`: Protect your server against mass nuking and destructive actions
- `antinuke list`: View all enabled modules along with whitelisted members & bots
- `antinuke config`: View detailed server configuration for AntiNuke
- `antinuke kick`: Prevent mass member kick (enable/disable)
- `antinuke ban`: Prevent mass member ban (enable/disable/threshold)
- `antinuke channel`: Prevent mass channel creation and deletion (enable/disable/create/delete)
- `antinuke role`: Prevent mass role deletion (enable/disable/threshold)
- `antinuke emoji`: Prevent mass emoji deletion (enable/disable/threshold)
- `antinuke webhook`: Prevent mass webhook creation (enable/disable/threshold)
- `antinuke botadd`: Prevent unauthorized bot additions (enable/disable/threshold)
- `antinuke permissions`: Watch for dangerous permission changes (enable/disable/add/remove)
- `antinuke admin`: Give a member permission to edit AntiNuke settings
- `antinuke admins`: View all AntiNuke admin users
- `antinuke whitelist`: Whitelist a member or bot from AntiNuke actions

### Snipe
- `snipe`: Retrieve a recently deleted message (with optional index)
- `editsnipe`: Retrieve a message's original text before it was edited (with optional index)
- `reactionsnipe`: Retrieve a deleted reaction from a message (with optional index)
- `reactionhistory`: See all logged reactions for a specific message
- `clearsnipe`: Clear all deleted messages from snipe history (requires Manage Messages)
- `removesnipe`: Remove a specific snipe from the snipe index (requires Manage Messages)
- `purgesnipe`: View messages that were deleted through a purge (requires Manage Messages)

### Crypto
- `crypto`: Check the current price of a specified cryptocurrency
- `transaction`: View detailed information about a Bitcoin or Ethereum transaction
- `subscribe`: Subscribe to a Bitcoin transaction and get notified upon first confirmation

### Logs
- `log`: Set up logging for your community and view current configuration
- `log add #channel event`: Add a logging event to a channel
- `log remove #channel event`: Remove an event from a logging channel
- `log ignore @member/#channel`: Ignore a member or channel from logging
- `log ignore list`: View all ignored members and channels

Available logging events:
- Message deleted/edited
- Member joined/left/banned/unbanned
- Member updated
- Role created/deleted/updated
- Channel created/deleted/updated
- Voice channel joined/left/moved

### Servers
- **Pin Archival System**: Archive and manage pinned messages
  - `pins`: View pin archival system commands
  - `pins set`: Enable or disable the pin archival system
  - `pins archive`: Archive the pins in the current channel
  - `pins channel`: Set the pin archival channel
  - `pins config`: View the pin archival config
  - `pins reset`: Reset the pin archival config
  - `pins unpin`: Enable or disable unpinning of messages during archival

- **Image-Only Channels**: Set up gallery channels that enforce image + caption rules
  - `imageonly`: Set up image + caption only channels
  - `imageonly add`: Add a gallery channel
  - `imageonly remove`: Remove a gallery channel
  - `imageonly list`: View all gallery channels

- **Fake Permissions**: Grant roles permission to use bot commands without Discord permissions
  - `fakepermissions`: Set up fake permissions for role through the bot
  - `fakepermissions add`: Grant a fake permission to a role
  - `fakepermissions remove`: Remove a fake permission from a role
  - `fakepermissions list`: List all fake permissions
  - `fakepermissions reset`: Reset all fake permissions

- **Message Filters**: Set up automatic message filtering in your server
  - `filter`: View a variety of options to help clean chat
  - `filter add`: Add a filtered word
  - `filter list`: View a list of filtered words in guild
  - `filter reset`: Reset all filtered words
  - `filter invites`: Delete any message that contains a server invite
  - `filter invites exempt`: Exempt roles from the invites filter
  - `filter invites exempt list`: View list of roles exempted from invites filter

### Counters
- `counter`: Create a category or channel that will keep track of the member or booster count
- `counter add`: Create channel counter (options: channel or type)
- `counter remove`: Remove a channel or category counter
- `counter list`: List every category or channel keeping track of members or boosters in this server

### AutoPfp
- `autopfp setup`: Setup and learn how to configure auto profile picture channels
- `autopfp set`: Set a channel to receive automatic profile pictures with custom categories
- `autopfp reset`: Reset all auto profile picture configurations
- `autobanner setup`: Setup and learn how to configure auto banner channels
- `autobanner set`: Set a channel to receive automatic banner images with custom categories
- `autobanner reset`: Reset all auto banner configurations

### Roleplay
- **Emotion Reactions**: Express how you feel towards other members
  - `surprised`: Show surprise towards a member
  - `mad`: Show anger towards a member
  - `sweat`: Show nervousness with sweat towards a member
  - `nervous`: Act nervous towards a member
  - `thumbsup`: Give a thumbs up to a member
  - `no`: Say no to a member
  - `woah`: Express amazement towards a member
  - `tired`: Show tiredness towards a member
  - `yawn`: Yawn at a member
  - `sad`: Express sadness towards a member
  - `cry`: Cry because of a member
  - `blush`: Blush because of a member
  - `smile`: Smile at a member
  - `laugh`: Laugh at a member

- **Physical Actions**: Interact physically with other members
  - `nom`: Pretend to eat/nom on a member
  - `poke`: Poke a member
  - `pinch`: Pinch a member
  - `pat`: Pat a member
  - `headpat`: Pat the head of a member
  - `hug`: Hug a member
  - `kiss`: Kiss a member
  - `airkiss`: Blow a kiss to a member
  - `slap`: Slap a member
  - `smack`: Smack a member
  - `bite`: Bite a member
  - `punch`: Punch a member
  - `tickle`: Tickle a member
  - `highfive`: Give a high five to a member
  - `brofist`: Give a brofist to a member
  - `handhold`: Hold hands with a member
  - `lick`: Lick a member
  - `nuzzle`: Nuzzle a member
  - `cuddle`: Cuddle with a member

- **Social Gestures**: Show social gestures towards other members
  - `wave`: Wave at a member
  - `shrug`: Shrug at a member
  - `stare`: Stare at a member
  - `angrystare`: Glare angrily at a member
  - `sip`: Sip tea while looking at a member
  - `sigh`: Sigh at a member
  - `slowclap`: Slow clap at a member
  - `clap`: Clap for a member
  - `facepalm`: Facepalm at a member
  - `sorry`: Apologize to a member
  - `celebrate`: Celebrate with a member
  - `cheers`: Cheers with a member
  - `dance`: Dance with a member
  - `shy`: Act shy around a member
  - `confused`: Show confusion towards a member
  - `huh`: Look confused at a member

All roleplay commands support optional custom messages and show anime-style GIFs for visual effect.

### VoiceMaster
- **Create and Manage Temporary Voice Channels**
  - `voicemaster`: Make temporary voice channels in your server
  - `voicemaster setup`: Begin VoiceMaster server configuration setup
  - `voicemaster reset`: Reset server configuration for VoiceMaster
  - `voicemaster category`: Redirect voice channels to custom category
  - `voicemaster defaultbitrate`: Edit default bitrate for new Voice Channels
  - `voicemaster defaultregion`: Edit default region for new Voice Channels
  - `voicemaster defaultrole`: Set a role that members get for being in a VM channel
  - `voicemaster configuration`: See current configuration for current voice channel
  - `voicemaster name`: Rename your voice channel
  - `voicemaster lock`: Lock your voice channel
  - `voicemaster unlock`: Unlock your voice channel
  - `voicemaster ghost`: Hide your voice channel
  - `voicemaster unghost`: Reveal your voice channel
  - `voicemaster limit`: Edit user limit of your voice channel
  - `voicemaster bitrate`: Edit bitrate of your voice channel
  - `voicemaster permit`: Permit a member or role to join your VC
  - `voicemaster reject`: Reject a member or role from joining your VC
  - `voicemaster claim`: Claim an inactive voice channel
  - `voicemaster transfer`: Transfer ownership of your channel to another member

### Pokemon
- `journey`: Start your Pokemon journey
- `catch`: Spawn a new Pokemon if you are allowed to
- `pokemon`: Lookup a Pokemon's stats
- `evolve`: Evolve the current primary Pokemon if available
- `battle`: Battle Pokemon for XP
- `moves`: Check new moves and reassign moves
- `pokedex`: See a member's Pokedex
- `pokestats`: View the stats of Pokemon across server
- `party`: View your primary Pokemon for battles
- `pc`: View all Pokemon in your PC storage (collection)
- `inventory`: View your inventory
- `shop`: Buy pokemon balls to higher your chances of catching a pokemon

## License

This project is licensed under the MIT License - see the LICENSE file for details.