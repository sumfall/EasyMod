# Imports
import interactions
from interactions import (
    Client,
    Intents,
    slash_command,
    SlashContext,
    OptionType,
    slash_option,
    check,
    integration_types,
)

BOT_TOKEN = open("token.txt", "r").read().strip()
bot = Client(intents=Intents.ALL, basic_logging=True)


# Print bot status
@interactions.listen()
async def on_startup():
    print("EasyMod is ready")


# Start bot
if __name__ == "__main__":
    bot.start(BOT_TOKEN)
