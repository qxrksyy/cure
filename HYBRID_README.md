# QxrK Discord Bot - Hybrid Setup

This Discord bot uses a hybrid system with both Python and Node.js components working together.

## Setup Instructions

1. **Install Requirements:**
   - Python requirements: `pip install -r requirements.txt`
   - Node.js requirements: `npm install`

2. **Environment Variables:**
   Create a `.env` file in the root directory with:
   ```
   TOKEN=your_discord_bot_token
   TENOR_API_KEY=your_tenor_api_key
   GIPHY_API_KEY=your_giphy_api_key
   API_PORT=3000
   ```

3. **Lavalink Setup (for Music):**
   - Lavalink is running on a Raspberry Pi at 10.0.0.75:2333
   - If setting up a new Raspberry Pi for Lavalink:
     1. Install Java 17 or newer on the Raspberry Pi
     2. Download Lavalink.jar from https://github.com/freyacodes/Lavalink/releases
     3. Create application.yml with the following configuration:
       ```yaml
       server:
         port: 2333
         address: 0.0.0.0  # Important: Use 0.0.0.0 to allow external connections
       lavalink:
         server:
           password: "Confusion10072003$"
           sources:
             youtube: true
             bandcamp: true
             soundcloud: true
             twitch: true
             vimeo: true
             http: true
             local: false
       ```
     4. Start Lavalink on the Pi with: `java -jar Lavalink.jar`

4. **Start the Bot:**
   - Use the `start_hybrid.bat` file to start both Node.js and Python components
   - Or manually:
     - Start Node.js bot: `npm start`
     - Start Python bot: `python bot.py`

## Music System

This bot uses **wavelink 3.2.0** for music playback through Python. The JavaScript music implementation (distube) is not active. All music commands should be used through the Python bot interface.

## Troubleshooting

- **Wavelink Connection Issues**: Make sure Lavalink is running on port 2333 before starting the bot.
- **JavaScript Bridge Issues**: The Node.js server must be running on port 3000 (or the port specified in the .env file).
- **Music Playback Issues**: Check that you've installed the correct wavelink version (3.2.0) and that Lavalink is properly configured.

## API Keys

The bot uses API keys for Tenor and Giphy. These should be set in the `.env` file rather than in `config/config.json` for security reasons.

## Important Files

- `js_bridge.py` - Python-side bridge for communication with JavaScript
- `src/utils/bridge-api.js` - JavaScript API server for receiving requests
- `cogs/voicemaster/voicemaster.py` - Python implementation of VoiceMaster functionality
- `src/commands/panel.js` - JavaScript implementation of the panel UI
- `src/utils/voicemaster.js` - JavaScript button handlers for the VoiceMaster panel

## Testing the Connection

You can use the `!checkjsbridge` command to verify if the Python bot can connect to the JavaScript bot.

## Fallback Mode

If the JavaScript bot is unavailable, the Python bot will automatically fall back to its own UI implementation. While this won't have the exact styling, it will ensure the functionality remains available. 