import asyncio
import discord
from redbot.core import commands, Config, checks
import discord.errors
from redbot.core.bot import Red

class RoleStuff(commands.Cog):

    default_user_settings = {'last_roles': {}}
    LETS_TALK_TIMEOUT = 60 * 60

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=524658401248992)
        self.config.register_user(**self.default_user_settings)

        self.lets_talk_timeout_task = None
        self.suppress_next_lets_chat_role_removal_message = False

        try:
            self.init_stuff()
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.init_stuff()

    def init_stuff(self):
        # TODO: unhardcode all of this PLEASE
        self.admin_channel = self.bot.get_channel(182254222694285312)
        self.debug_channel = self.bot.get_channel(412381738510319626)
        self.lets_chat_channel = self.bot.get_channel(683769319259111549)
        self.lets_chat_role = self.lets_chat_channel.guild.get_role(683768446680563725)
        self.player_role = self.lets_chat_channel.guild.get_role(182284445837950977)
        self.spacebee = self.admin_channel.guild.get_member(182251046783942656)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not hasattr(self, "spacebee"):
            self.init_stuff()
        user_data = await self.config.user(member).last_roles()
        if len(member.roles) > 1:
            user_data[str(member.guild.id)] = [role.id for role in member.roles][1:]
            await self.config.user(member).last_roles.set(user_data)

    async def remove_lets_chat_role_after_time(self, time: int, member: discord.Member):
        await asyncio.sleep(time)
        if self.lets_chat_role in member.roles:
            try:
                await member.remove_roles(self.lets_chat_role, reason="timeout")
                await self.lets_chat_channel.send(f"Automatically removing {self.lets_chat_role.mention} from {member.mention} because its duration ({self.LETS_TALK_TIMEOUT / 60:.0f} minutes) expired.")
            except:
                import traceback
                return await self.bot.send_to_owners(traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self.lets_chat_role in after.roles and self.lets_chat_role not in before.roles:
            dm_channel = after.dm_channel
            if dm_channel is None:
                dm_channel = await after.create_dm()
            for member in self.lets_chat_role.members:
                if member != after:
                    self.suppress_next_lets_chat_role_removal_message = True
                    await member.remove_roles(self.lets_chat_role, reason="someone else entering Let's Chat")
                    await self.admin_channel.send(f"Automatically removing {self.lets_chat_role.mention} from {member.mention} because {after.mention} is now being talked to.")
            # await self.debug_channel.send(f"{after.mention} now has role {self.lets_chat_role.mention}, total number of people with this role: {len(self.lets_chat_role.members)}")
            await after.remove_roles(self.player_role, reason=f"entering Let's Chat")
            em = discord.Embed(description=f"Beginning conversation with {after.mention}", colour=discord.Colour.from_rgb(80, 140, 80))
            em.set_footer(text=f"{after.id}")
            await self.lets_chat_channel.send(embed=em)
            self.lets_talk_timeout_task = asyncio.create_task(self.remove_lets_chat_role_after_time(self.LETS_TALK_TIMEOUT, after))
            try:
                result = await dm_channel.send(f"""Hi! An admin in the Goonstation Discord would like to talk to you. Please click here <#{self.lets_chat_channel.id}> and send a message there so that we know you've seen this. Please don't click away from the channel, or else you'll lose the scrollback. Thank you!\n(If the channel is no longer accessible when you read this message please use the `]report` command to contact admins instead.)""")
            except discord.errors.Forbidden:
                try:
                    await self.lets_chat_channel.send(f"""Hi {after.mention}! An admin would like to talk to you. Please send a message here to know that you've seen this. Please don't click away from the channel, or else you'll lose the scrollback. Thank you!""")
                except Exception as e:
                    await self.debug_channel.send("Let's Talk stuff crashed, notify the user yourself!")
            # await self.lets_chat_channel.edit(name="lets-talk\N{Police Cars Revolving Light}")
        elif self.lets_chat_role not in after.roles and self.lets_chat_role in before.roles:
            if self.lets_talk_timeout_task:
                self.lets_talk_timeout_task.cancel()
                self.lets_talk_timeout_task = None
            await after.add_roles(self.player_role, reason=f"leaving Let's Chat")
            em = discord.Embed(description=f"Ending conversation with {after.mention}", colour=discord.Colour.from_rgb(140, 80, 80))
            em.set_footer(text=f"{after.id}")
            if not self.suppress_next_lets_chat_role_removal_message:
                await self.lets_chat_channel.send(embed=em)
            else:
                self.suppress_next_lets_chat_role_removal_message = False
            # await self.lets_chat_channel.edit(name="lets-talk")
            # await self.debug_channel.send(f"{after.mention} lost the role {self.lets_chat_role.mention}, total number of people with this role: {len(self.lets_chat_role.members)}")

    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def lastroles(self, ctx: commands.Context, user: discord.User):
        """Shows a list of roles an user had the last time they left the guild."""
        user_data = await self.config.user(user).last_roles()
        guild_id = str(ctx.guild.id)
        if guild_id not in user_data:
            return await ctx.send("Never heard of them.")
        roles = []
        unsuccessful_count = 0
        for role_id in user_data[guild_id]:
            role = ctx.guild.get_role(role_id)
            if role:
                roles.append(role)
            else:
                unsuccessful_count += 1
        reply = ""
        if len(roles) == 0:
            reply += "No existing roles found. "
        else:
            reply += "Last roles: " + ', '.join(role.name for role in roles) + ". "
        if unsuccessful_count > 0:
            reply += f"Number of removed roles they had: {unsuccessful_count}."
        await ctx.send(reply)



    @commands.command()
    @checks.mod_or_permissions(manage_roles=True)
    async def restoreroles(self, ctx: commands.Context, member: discord.Member):
        """Tries to restore a member's roles to what they had the last time they left."""
        user_data = await self.config.user(member).last_roles()
        guild_id = str(ctx.guild.id)
        if guild_id not in user_data:
            return await ctx.send("Never heard of them.")
        roles_to_add = []
        unsuccessful_count = 0
        for role_id in user_data[guild_id]:
            role = ctx.guild.get_role(role_id)
            if role == self.lets_chat_role:
                continue
            if role:
                roles_to_add.append(role)
            else:
                unsuccessful_count += 1
        await member.add_roles(*roles_to_add, reason=f"restored last roles at the request of {ctx.message.author}")
        reply = ""
        if len(roles_to_add) == 0:
            reply += "Restored no roles. "
        else:
            reply += "Restored roles " + ', '.join(role.name for role in roles_to_add) + ". "
        if unsuccessful_count > 0:
            reply += f"Failed to restore {unsuccessful_count} roles."
        await ctx.send(reply)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not hasattr(self, "spacebee"):
            self.init_stuff()
        try:
            if message.author == self.spacebee and message.content == "Youre already linked!":
                async for msg in message.channel.history(limit=10):
                    if msg.content.startswith(".link") or msg.content.startswith("!link"):
                        author = msg.author
                        if self.player_role not in author.roles:
                            await author.add_roles(self.player_role, reason=f"already linked via .link")
                            await self.debug_channel.send(f"Gave {self.player_role.name} to {author.mention}.")
                            return

            return # disabling feature for now as Spacebee is broken
            if message.content.startswith(".link") or message.content.startswith("!link") or message.content.startswith("]debuglink"):
                tries = 10
                while self.player_role not in message.author.roles and tries > 0:
                    tries -= 1
                    await asyncio.sleep(60)
                    if self.player_role in message.author.roles:
                        return
                    await self.debug_channel.send(f".keyof {message.author.mention}")
                    def check(m):
                        return m.author == self.spacebee
                    try:
                        msg = await self.bot.wait_for('message', check=check, timeout=60)
                    except asyncio.TimeoutError:
                        continue
                    if not msg:
                        continue
                    if msg.content.startswith("Their key is ") and \
                            self.player_role not in message.author.roles and \
                            "<not associated>" not in msg.content:
                        await message.author.add_roles(self.player_role, reason=f"linked via .link")
                        await self.debug_channel.send(f"Gave {self.player_role.name} to {message.author.mention}.")
                        return
        except Exception as e:
            import traceback
            return await self.bot.send_to_owners(traceback.format_exc())
    


