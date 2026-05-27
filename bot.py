import discord
from discord import app_commands
from discord.ext import commands
import os
import datetime

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="$unused$", intents=intents)

RULES_MESSAGE = (
    "1. **Be respectful** — Treat everyone with kindness. No harassment, hate speech, or bullying.\n"
    "2. **No spam** — Don't flood the chat with repeated messages or excessive mentions.\n"
    "3. **Keep it relevant** — Post content in the appropriate channels.\n"
    "4. **No NSFW content** — This is a safe-for-work community.\n"
    "5. **No advertising** — Don't promote other servers or services without permission.\n"
    "6. **Follow Discord's ToS** — https://discord.com/terms\n\n"
    "By being in this server, you agree to follow these rules. Violations may result in a mute, kick, or ban."
)

async def get_mod_log_channel(guild):
    channel = discord.utils.get(guild.text_channels, name="mod-log")
    if channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel("mod-log", overwrites=overwrites)
    return channel

async def send_mod_log(guild, *, title, color, moderator, target=None, reason=None, extra=None):
    channel = await get_mod_log_channel(guild)
    embed = discord.Embed(title=title, color=color, timestamp=datetime.datetime.utcnow())
    if target:
        embed.add_field(name="Member", value=f"{target} (`{target.id}`)", inline=False)
    embed.add_field(name="Moderator", value=f"{moderator} (`{moderator.id}`)", inline=False)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    if extra:
        for k, v in extra.items():
            embed.add_field(name=k, value=v, inline=False)
    embed.set_footer(text=f"Server: {guild.name}")
    await channel.send(embed=embed)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        except Exception as e:
            print(f"Failed to sync to {guild.name}: {e}")
    print(f"✅ {bot.user} is online and slash commands are synced!")

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel is None:
        channel = member.guild.system_channel
    if channel:
        embed = discord.Embed(
            title=f"👋 Welcome to {member.guild.name}!",
            description=(
                f"Hey {member.mention}, welcome to the server! 🎉\n\n"
                "Make sure to read the rules and enjoy your stay!"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

@bot.tree.command(name="rules", description="Post the server rules")
async def rules(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Server Rules",
        description=RULES_MESSAGE,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check the bot's response time")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")

@bot.tree.command(name="say", description="Make the bot send a message")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(message="The message you want the bot to send")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("✅ Message sent!", ephemeral=True)
    await interaction.channel.send(message)

class EmbedBuilderView(discord.ui.View):
    def __init__(self, author_id, channel, preview_message=None):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.channel = channel
        self.preview_message = preview_message
        self.data = {
            "title": None,
            "description": None,
            "color": 0x5865F2,
            "footer": None,
            "image": None,
            "thumbnail": None,
            "fields": []
        }

    def build_embed(self, preview=False):
        embed = discord.Embed(color=self.data["color"])
        embed.title = self.data["title"] or ("📋 Embed Preview" if preview else None)
        embed.description = self.data["description"] or ("*No description set yet.*" if preview else None)
        if self.data["footer"]:
            embed.set_footer(text=self.data["footer"])
        if self.data["image"]:
            embed.set_image(url=self.data["image"])
        if self.data["thumbnail"]:
            embed.set_thumbnail(url=self.data["thumbnail"])
        for f in self.data["fields"]:
            embed.add_field(name=f["name"], value=f["value"], inline=f["inline"])
        return embed

    async def update_preview(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_embed(preview=True), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Only the person who ran this command can use these buttons.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Title & Description", emoji="📝", style=discord.ButtonStyle.secondary, row=0)
    async def edit_title_desc(self, interaction: discord.Interaction, button: discord.ui.Button):
        class TitleDescModal(discord.ui.Modal, title="Edit Title & Description"):
            t = discord.ui.TextInput(label="Title", placeholder="Embed title...", required=False, max_length=256,
                                     default=self.data.get("title") or "")
            d = discord.ui.TextInput(label="Description", placeholder="Embed body text...", required=False,
                                     style=discord.TextStyle.paragraph, max_length=4000,
                                     default=self.data.get("description") or "")
            async def on_submit(modal_self, inter):
                self.data["title"] = modal_self.t.value.strip() or None
                self.data["description"] = modal_self.d.value.strip() or None
                await self.update_preview(inter)
        await interaction.response.send_modal(TitleDescModal())

    @discord.ui.button(label="Color", emoji="🎨", style=discord.ButtonStyle.secondary, row=0)
    async def edit_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        class ColorModal(discord.ui.Modal, title="Set Color"):
            c = discord.ui.TextInput(label="Hex Color", placeholder="e.g. FF5733 or #FF5733", max_length=7)
            async def on_submit(modal_self, inter):
                hex_str = modal_self.c.value.strip().lstrip("#")
                try:
                    self.data["color"] = int(hex_str, 16)
                    await self.update_preview(inter)
                except ValueError:
                    await inter.response.send_message("❌ Invalid color. Use a hex code like `FF5733`.", ephemeral=True)
        await interaction.response.send_modal(ColorModal())

    @discord.ui.button(label="Footer", emoji="📄", style=discord.ButtonStyle.secondary, row=0)
    async def edit_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        class FooterModal(discord.ui.Modal, title="Set Footer"):
            f = discord.ui.TextInput(label="Footer Text", placeholder="e.g. Posted by Admins", required=False,
                                     max_length=2048, default=self.data.get("footer") or "")
            async def on_submit(modal_self, inter):
                self.data["footer"] = modal_self.f.value.strip() or None
                await self.update_preview(inter)
        await interaction.response.send_modal(FooterModal())

    @discord.ui.button(label="Images", emoji="🖼️", style=discord.ButtonStyle.secondary, row=0)
    async def edit_images(self, interaction: discord.Interaction, button: discord.ui.Button):
        class ImagesModal(discord.ui.Modal, title="Set Images"):
            img = discord.ui.TextInput(label="Large Image URL", placeholder="https://example.com/image.png",
                                       required=False, max_length=500, default=self.data.get("image") or "")
            thumb = discord.ui.TextInput(label="Thumbnail URL (top-right corner)", placeholder="https://example.com/thumb.png",
                                         required=False, max_length=500, default=self.data.get("thumbnail") or "")
            async def on_submit(modal_self, inter):
                self.data["image"] = modal_self.img.value.strip() or None
                self.data["thumbnail"] = modal_self.thumb.value.strip() or None
                await self.update_preview(inter)
        await interaction.response.send_modal(ImagesModal())

    @discord.ui.button(label="Add Field", emoji="➕", style=discord.ButtonStyle.secondary, row=1)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.data["fields"]) >= 25:
            await interaction.response.send_message("❌ Maximum of 25 fields reached.", ephemeral=True)
            return
        class FieldModal(discord.ui.Modal, title="Add Field"):
            name = discord.ui.TextInput(label="Field Name", placeholder="e.g. Rules", max_length=256)
            value = discord.ui.TextInput(label="Field Value", placeholder="e.g. Be respectful!",
                                         style=discord.TextStyle.paragraph, max_length=1024)
            inline = discord.ui.TextInput(label="Inline? (yes/no)", placeholder="yes", max_length=3, default="no")
            async def on_submit(modal_self, inter):
                self.data["fields"].append({
                    "name": modal_self.name.value,
                    "value": modal_self.value.value,
                    "inline": modal_self.inline.value.strip().lower() == "yes"
                })
                await self.update_preview(inter)
        await interaction.response.send_modal(FieldModal())

    @discord.ui.button(label="Clear Fields", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def clear_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.data["fields"] = []
        await self.update_preview(interaction)

    @discord.ui.button(label="Send Embed", emoji="✅", style=discord.ButtonStyle.success, row=1)
    async def send_embed_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.data["title"] and not self.data["description"] and not self.data["fields"]:
            await interaction.response.send_message("❌ Add at least a title or description before sending.", ephemeral=True)
            return
        final_embed = self.build_embed(preview=False)
        await self.channel.send(embed=final_embed)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="✅ **Embed sent!**", embed=None, view=self)
        self.stop()

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.danger, row=1)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="❌ **Embed builder cancelled.**", embed=None, view=self)
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.preview_message:
            try:
                await self.preview_message.edit(content="⏰ Embed builder timed out.", embed=None, view=self)
            except Exception:
                pass

@bot.tree.command(name="createembed", description="Open the interactive embed builder")
@app_commands.checks.has_permissions(manage_messages=True)
async def createembed(interaction: discord.Interaction):
    view = EmbedBuilderView(author_id=interaction.user.id, channel=interaction.channel)
    preview = view.build_embed(preview=True)
    await interaction.response.send_message(
        content="### 🛠️ Embed Builder\nUse the buttons below to build your embed. Click **Send Embed** when done.",
        embed=preview,
        view=view,
        ephemeral=True
    )
    view.preview_message = await interaction.original_response()

@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(member="The member to kick", reason="Reason for the kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member == interaction.user:
        await interaction.response.send_message("❌ You can't kick yourself.", ephemeral=True)
        return
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ You can't kick someone with an equal or higher role.", ephemeral=True)
        return
    await member.kick(reason=reason)
    embed = discord.Embed(title="👢 Member Kicked",
                          description=f"**{member}** has been kicked.\n**Reason:** {reason}",
                          color=discord.Color.orange())
    embed.set_footer(text=f"Actioned by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    await send_mod_log(interaction.guild, title="👢 Member Kicked", color=discord.Color.orange(),
                       moderator=interaction.user, target=member, reason=reason)

@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(member="The member to ban", reason="Reason for the ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member == interaction.user:
        await interaction.response.send_message("❌ You can't ban yourself.", ephemeral=True)
        return
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ You can't ban someone with an equal or higher role.", ephemeral=True)
        return
    await member.ban(reason=reason)
    embed = discord.Embed(title="🔨 Member Banned",
                          description=f"**{member}** has been banned.\n**Reason:** {reason}",
                          color=discord.Color.red())
    embed.set_footer(text=f"Actioned by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    await send_mod_log(interaction.guild, title="🔨 Member Banned", color=discord.Color.red(),
                       moderator=interaction.user, target=member, reason=reason)

@bot.tree.command(name="unban", description="Unban a previously banned user")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(username="Exact username of the banned user, e.g. Username#0000")
async def unban(interaction: discord.Interaction, username: str):
    await interaction.response.defer()
    banned_users = [entry async for entry in interaction.guild.bans()]
    for entry in banned_users:
        if str(entry.user) == username:
            await interaction.guild.unban(entry.user)
            embed = discord.Embed(title="✅ Member Unbanned",
                                  description=f"**{entry.user}** has been unbanned.",
                                  color=discord.Color.green())
            embed.set_footer(text=f"Actioned by {interaction.user}")
            await interaction.followup.send(embed=embed)
            await send_mod_log(interaction.guild, title="✅ Member Unbanned", color=discord.Color.green(),
                               moderator=interaction.user, target=entry.user)
            return
    await interaction.followup.send(f"❌ No banned user found with the name `{username}`.")

@bot.tree.command(name="mute", description="Mute (timeout) a member")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(member="The member to mute", minutes="Duration in minutes (default: 10)", reason="Reason for the mute")
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "No reason provided"):
    if member == interaction.user:
        await interaction.response.send_message("❌ You can't mute yourself.", ephemeral=True)
        return
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ You can't mute someone with an equal or higher role.", ephemeral=True)
        return
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    embed = discord.Embed(title="🔇 Member Muted",
                          description=f"**{member}** has been muted for **{minutes} minute(s)**.\n**Reason:** {reason}",
                          color=discord.Color.dark_gray())
    embed.set_footer(text=f"Actioned by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    await send_mod_log(interaction.guild, title="🔇 Member Muted", color=discord.Color.dark_gray(),
                       moderator=interaction.user, target=member, reason=reason,
                       extra={"Duration": f"{minutes} minute(s)"})

@bot.tree.command(name="timeout", description="Timeout a member and DM them")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(member="The member to timeout", minutes="Duration in minutes (default: 10)", reason="Reason for the timeout")
async def timeout_member(interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "No reason provided"):
    if member == interaction.user:
        await interaction.response.send_message("❌ You can't timeout yourself.", ephemeral=True)
        return
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ You can't timeout someone with an equal or higher role.", ephemeral=True)
        return
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    embed = discord.Embed(title="⏱️ Member Timed Out",
                          description=f"**{member}** has been timed out for **{minutes} minute(s)**.\n**Reason:** {reason}",
                          color=discord.Color.dark_orange())
    embed.set_footer(text=f"Actioned by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    try:
        await member.send(f"⏱️ You have been timed out in **{interaction.guild.name}** for **{minutes} minute(s)**.\n**Reason:** {reason}")
    except discord.Forbidden:
        pass
    await send_mod_log(interaction.guild, title="⏱️ Member Timed Out", color=discord.Color.dark_orange(),
                       moderator=interaction.user, target=member, reason=reason,
                       extra={"Duration": f"{minutes} minute(s)"})

@bot.tree.command(name="untimeout", description="Remove an active timeout from a member")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(member="The member to remove the timeout from")
async def untimeout_member(interaction: discord.Interaction, member: discord.Member):
    if not member.is_timed_out():
        await interaction.response.send_message(f"❌ **{member}** is not currently timed out.", ephemeral=True)
        return
    await member.timeout(None)
    embed = discord.Embed(title="✅ Timeout Removed",
                          description=f"**{member}**'s timeout has been lifted.",
                          color=discord.Color.green())
    embed.set_footer(text=f"Actioned by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    await send_mod_log(interaction.guild, title="✅ Timeout Removed", color=discord.Color.green(),
                       moderator=interaction.user, target=member)

@bot.tree.command(name="slowmode", description="Set slowmode delay for this channel")
@app_commands.checks.has_permissions(manage_channels=True)
@app_commands.describe(seconds="Delay in seconds (0 = off, max 21600)")
async def slowmode(interaction: discord.Interaction, seconds: int = 0):
    if seconds < 0 or seconds > 21600:
        await interaction.response.send_message("❌ Slowmode must be between 0 (off) and 21600 seconds.", ephemeral=True)
        return
    await interaction.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        embed = discord.Embed(title="💬 Slowmode Disabled",
                              description=f"Slowmode has been turned off in {interaction.channel.mention}.",
                              color=discord.Color.green())
    else:
        embed = discord.Embed(title="🐢 Slowmode Enabled",
                              description=f"Slowmode set to **{seconds} second(s)** in {interaction.channel.mention}.",
                              color=discord.Color.orange())
    embed.set_footer(text=f"Set by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    await send_mod_log(interaction.guild, title="🐢 Slowmode Changed", color=discord.Color.orange(),
                       moderator=interaction.user,
                       extra={"Channel": interaction.channel.mention,
                              "Slowmode": "Disabled" if seconds == 0 else f"{seconds} second(s)"})

@bot.tree.command(name="warn", description="Warn a member and DM them")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(member="The member to warn", reason="Reason for the warning")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    embed = discord.Embed(title="⚠️ Member Warned",
                          description=f"**{member.mention}** has been warned.\n**Reason:** {reason}",
                          color=discord.Color.yellow())
    embed.set_footer(text=f"Actioned by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    try:
        await member.send(f"⚠️ You have been warned in **{interaction.guild.name}**.\n**Reason:** {reason}")
    except discord.Forbidden:
        pass
    await send_mod_log(interaction.guild, title="⚠️ Member Warned", color=discord.Color.yellow(),
                       moderator=interaction.user, target=member, reason=reason)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.errors.CommandInvokeError):
        await interaction.response.send_message("❌ Something went wrong. Please try again.", ephemeral=True)
        print(f"Command error: {error}")
    else:
        await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        print(f"Unhandled error: {error}")

token = os.environ.get("DISCORD_TOKEN")
if not token:
    print("❌ ERROR: DISCORD_TOKEN secret is not set!")
else:
    bot.run(token)
