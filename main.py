# Imports
import interactions
import datetime
import traceback
import re
from interactions import (
    Client,
    Intents,
    slash_command,
    SlashContext,
    OptionType,
    slash_option,
    check,
    is_owner,
    Permissions,
    Member,
    errors,
)

BOT_TOKEN = open("token.txt", "r").read().strip()
bot = Client(intents=Intents.ALL, basic_logging=True)


# Print bot status
@interactions.listen()
async def on_startup():
    print("EasyMod is ready")


# /timeout logic
def timeout_time_logic(duration_str: str) -> datetime.timedelta | None:
    regex = re.compile(r"(\d+)\s*([smhdw])")
    matches = regex.findall(duration_str.lower())
    if not matches:
        return None

    total_seconds = 0
    # Calculate total seconds
    for value, unit in matches:
        try:
            value = int(value)
        except ValueError:
            return None
        if unit == "s":
            total_seconds += value
        elif unit == "m":
            total_seconds += value * 60
        elif unit == "h":
            total_seconds += value * 3600  # 60 * 60
        elif unit == "d":
            total_seconds += value * 86400  # 24 * 60 * 60
        elif unit == "w":
            total_seconds += value * 604800  # 7 * 24 * 60 * 60

    # Check if time is positive
    if total_seconds <= 0:
        return None

    delta = datetime.timedelta(seconds=total_seconds)

    # Check against Discord's maximum timeout time
    if delta > datetime.timedelta(days=28):
        return None

    return delta


# Slash commands
# /say
@slash_command(
    name="say", description="Makes the bot say what its owner wants it to say:"
)
@check(is_owner())
@slash_option(
    name="text",
    description="Adds text",
    required=False,
    opt_type=OptionType.STRING,
)
async def channel_function(ctx: SlashContext, text: str = None):
    if not text:
        print("ERROR: Please select an option")
        await ctx.send("ERROR: Please select an option", ephemeral=True)
    elif text:
        print("Sent: " + text)
        await ctx.send(text)


# /timeout
@slash_command(
    name="timeout",
    description="Times out a user for a set amount of time",
    default_member_permissions=Permissions.MODERATE_MEMBERS,
)
# /timeout ommand options
@slash_option(
    name="user",
    description="Who do you wanna timeout?",
    required=True,
    opt_type=OptionType.USER,
)
@slash_option(
    name="duration",
    description="Amount of time (Max 28d)",
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="reason",
    description="Reason (optional)",
    required=False,
    opt_type=OptionType.STRING,
)
async def timeout_command(
    ctx: SlashContext, user: Member, duration: str, reason: str | None = None
):
    if not ctx.guild or not isinstance(ctx.author, Member):
        await ctx.send(
            "Command must be run in a server and you need mod perms", ephemeral=True
        )
        return
    # Stops you from doing a stupid
    if user == ctx.author or user.id == ctx.bot.user.id:
        await ctx.send("You can't time yourself or the bot out lmao", ephemeral=True)
        return

    delta = timeout_time_logic(duration)
    if delta is None:
        await ctx.send("Invalid time (max 28d use s/m/h/d/w)", ephemeral=True)
        return

    # Perm checks
    try:
        # Find the server owner
        guild_owner = await ctx.guild.fetch_owner()
        # Stops you from timing out the server owner
        if user == guild_owner:
            await ctx.send("Cannot timeout the server owner", ephemeral=True)
            return

        author: Member = ctx.author
        bot_member = await ctx.guild.fetch_member(ctx.bot.user.id)
        if not bot_member:
            raise Exception("Bot member object not found in the server")
        if (
            author != guild_owner
            and user.top_role
            and (not author.top_role or user.top_role >= author.top_role)
        ):
            await ctx.send(
                "Your role is not high enough to timeout this user", ephemeral=True
            )
            return
        if user.top_role and (
            not bot_member.top_role or user.top_role >= bot_member.top_role
        ):
            await ctx.send(
                "My role is not high enough to timeout this user", ephemeral=True
            )
            return

    except Exception as e:
        # Log and report errors during checks
        print(f"Hierarchy check error: {e}")  # Log essential errors
        await ctx.send("An error occurred while checking roles", ephemeral=True)
        return

    # Timeout
    try:
        expires_at = datetime.datetime.now(datetime.timezone.utc) + delta
        await user.timeout(communication_disabled_until=expires_at, reason=reason)

        # Format confirmation message
        reason_text = f" Reason: {reason}" if reason else ""
        await ctx.send(
            f"✅ Timed out {user.mention} until <t:{int(expires_at.timestamp())}:F> ({delta}).{reason_text}"
        )

    # Error Handling
    except errors.Forbidden:
        await ctx.send("❌ Permission denied or my role is too low", ephemeral=True)
    except errors.HTTPException as e:
        await ctx.send(f"❌ Discord API error: {e.status}", ephemeral=True)
    except OverflowError:
        await ctx.send(
            "Invalid date calculation (duration likely too long)", ephemeral=True
        )
    except Exception as e:
        print(f"Timeout error: {e}")
        traceback.print_exc()  # Log detailed traceback for unexpected errors
        await ctx.send("❌ An unexpected error occurred", ephemeral=True)


# Start bot
if __name__ == "__main__":
    bot.start(BOT_TOKEN)
