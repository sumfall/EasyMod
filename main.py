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


# Timekeeping logic
def timeout_time_logic(duration_str: str) -> datetime.timedelta | None:
    regex = re.compile(r"(\d+)\s*([smhdw])")
    matches = regex.findall(duration_str.lower())
    if not matches:
        return None

    global total_seconds
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
    name="say", description="Makes the bot say what its owner wants it to say"
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
        await ctx.send("❌ Please select an option", ephemeral=True)
    elif text:
        print("Sent: " + text)
        await ctx.send(text)


# /timeout
@slash_command(
    name="timeout",
    description="Manages user timeouts",
    default_member_permissions=Permissions.MODERATE_MEMBERS,
    # scope=YOUR_GUILD_ID_HERE # Server id
)
async def timeout_base_command(ctx: SlashContext):
    # The main /timeout command itself won't be called directly by the secondary commands
    pass


# /timeout add
@timeout_base_command.subcommand(
    sub_cmd_name="add",
    sub_cmd_description="Timesout a user for a set amount of time",
)
# /timeout add command options
@slash_option(
    name="user",
    description="Who do you wanna timeout?",
    required=True,
    opt_type=OptionType.USER,
)
@slash_option(
    name="duration",
    description="Amount of time (1s, 1m, 1h, 1d, 1w, 28 days max)",  # Timestamp format
    required=True,
    opt_type=OptionType.STRING,
)
@slash_option(
    name="reason",
    description="Timeout reason (optional)",
    required=False,
    opt_type=OptionType.STRING,
)
async def timeout_add_subcommand(
    ctx: SlashContext, user: Member, duration: str, reason: str | None = None
):
    # /timeout add logic
    if not ctx.guild or not isinstance(ctx.author, Member):
        await ctx.send(
            "❌ Command must be run in a server and you need mod perms", ephemeral=True
        )
        return
    # Stops you from doing a stupid lol
    if user == ctx.author or user.id == ctx.bot.user.id:
        await ctx.send("❌ You can't time yourself or the bot out lmao", ephemeral=True)
        return

    delta = timeout_time_logic(duration)
    if delta is None:
        await ctx.send(
            "❌ Invalid time format or duration (1s, 1m, 1h, 1d, 1w, 28 days max)",
            ephemeral=True,
        )
        return

    # Perm checks
    try:
        # Finds the server owner
        server_owner = await ctx.guild.fetch_owner()
        # Stops you from timing out the server owner
        if user == server_owner:
            await ctx.send("❌ You can't timeout the server owner", ephemeral=True)
            return

        author: Member = ctx.author
        bot_id = await ctx.guild.fetch_member(ctx.bot.user.id)
        if not bot_id:
            await ctx.send("❌ Internal error: Couldn't find bot id", ephemeral=True)
            print("ERROR: Bot id object not found in the server")
            return

        # Check author's perms
        if (
            author != server_owner  # Owner bypasses perm check
            and user.top_role  # Check user roles
            and (
                not author.top_role or user.top_role >= author.top_role
            )  # Compare roles
        ):
            await ctx.send(
                "❌ Your role isn't high enough to timeout that user", ephemeral=True
            )
            return

        # Check bot's perms
        if user.top_role and (  # Check users roles
            not bot_id.top_role or user.top_role >= bot_id.top_role  # Compare roles
        ):
            await ctx.send(
                "❌ My role isn't high enough to timeout that user", ephemeral=True
            )
            return

    except Exception as e:
        # Log and report errors during checks
        print(f"Hierarchy check error: {e}")  # Log essential errors
        traceback.print_exc()  # Print full traceback for debugging
        await ctx.send("❌ An error occurred while checking roles", ephemeral=True)
        return

    try:
        tend_time = datetime.datetime.now(datetime.timezone.utc) + delta
        await user.timeout(communication_disabled_until=tend_time, reason=reason)

        # Format confirmation message
        reason_text = f" because {reason}" if reason else ""

        if total_seconds >= 86400:
            delta1 = str(delta)
            await ctx.send(
                f"✅ Timeout added for {user.mention} for {delta1.replace(", 0:00:00", "")}{reason_text}"
            )
            print(
                f"✅ Timeout added for {user.mention} until <t:{int(tend_time.timestamp())}:F> for {delta1.replace(", 0:00:00", "")}{reason_text}"
            )
        else:
            await ctx.send(
                f"✅ Timeout added for {user.mention} for {delta}{reason_text}"
            )
        print(
            f"✅ Timeout added for {user.mention} until <t:{int(tend_time.timestamp())}:F> for {delta}{reason_text}"
        )

    # Error Handling
    except errors.Forbidden:
        await ctx.send(
            "❌ Permission denied: Check my perms and roles",
            ephemeral=True,
        )
        print(f"ERROR: Forbidden - Cannot timeout {user}. Check permissions/roles")
    except errors.HTTPException as e:
        await ctx.send(f"❌ Discord API error: {e.status} - {e.text}", ephemeral=True)
        print(f"ERROR: HTTP Exception {e.status} - {e.text}")
    except OverflowError:  # Should be less likely with delta check
        await ctx.send(
            "❌ Invalid date calculation (duration likely too long)", ephemeral=True
        )
        print("ERROR: OverflowError during timeout calculation")
    except Exception as e:
        print(f"Timeout error: {e}")
        traceback.print_exc()  # Log detailed traceback for unexpected errors
        await ctx.send(
            "❌ An unexpected error occurred while applying the timeout",
            ephemeral=True,
        )


# /timeout remove
@timeout_base_command.subcommand(
    sub_cmd_name="remove",
    sub_cmd_description="Removes a users timeout",
)
# /timeout remove command options
@slash_option(
    name="user",
    description="Whos timeout do you wanna remove?",
    required=True,
    opt_type=OptionType.USER,
)
@slash_option(
    name="reason",
    description="Reason for removing timeout (optional)",
    required=False,
    opt_type=OptionType.STRING,
)
async def timeout_remove_subcommand(
    ctx: SlashContext, user: Member, reason: str | None = None
):
    if not ctx.guild or not isinstance(ctx.author, Member):
        await ctx.send(
            "❌ Command must be run in a server and you need mod perms", ephemeral=True
        )
        return

    # Check if the user is actually timedout
    if user.communication_disabled_until is None:
        await ctx.send(f"❌ {user.mention} isn't timedout", ephemeral=True)
        return

    # Perm checks
    try:
        server_owner = await ctx.guild.fetch_owner()
        author: Member = ctx.author
        bot_id = await ctx.guild.fetch_member(ctx.bot.user.id)

        if not bot_id:
            await ctx.send("❌ Internal error: Could not find bot id", ephemeral=True)
            print("ERROR: Bot id object not found in the server")
            return

        # Check author's roles
        if (
            author != server_owner
            and user.top_role
            and (not author.top_role or user.top_role >= author.top_role)
        ):
            await ctx.send(
                "❌ Your role is not high enough to manage this user's timeout",
                ephemeral=True,
            )
            return

        # Check bot's roles
        if user.top_role and (not bot_id.top_role or user.top_role >= bot_id.top_role):
            await ctx.send(
                "❌ My role isn't high enough to remove that users timeout",
                ephemeral=True,
            )
            return

    except Exception as e:
        print(f"Hierarchy check error (remove timeout): {e}")
        traceback.print_exc()
        await ctx.send("❌ An error occurred while checking roles", ephemeral=True)
        return

    # Remove timeout
    try:
        await user.timeout(
            communication_disabled_until=None,
            reason=reason or f"Timeout removed by {author}]",
        )

        reason_text = f" because {reason}" if reason else ""
        await ctx.send(f"✅ Timeout removed for {user.mention}{reason_text}")
        print(f"Removed timeout for {user}{reason or 'None'}")

    # Error Handling
    except errors.Forbidden:
        await ctx.send(
            "❌ Permission denied: Check my permissions and roles",
            ephemeral=True,
        )
        print(f"ERROR: Forbidden - Cannot remove timeout for {user}. Check perms/roles")
    except errors.HTTPException as e:
        await ctx.send(f"❌ Discord API error: {e.status} - {e.text}", ephemeral=True)
        print(f"ERROR: HTTP Exception {e.status} - {e.text}")
    except Exception as e:
        print(f"Remove timeout error: {e}")
        traceback.print_exc()
        await ctx.send(
            "❌ An unexpected error occurred while removing the timeout",
            ephemeral=True,
        )


# Start bot
if __name__ == "__main__":
    try:
        bot.start(BOT_TOKEN)
    except FileNotFoundError:
        print("ERROR: token.txt not found. Please create it in this same directory")
    except Exception as e:
        print(f"ERROR: Failed to start bot - {e}")
        traceback.print_exc()
