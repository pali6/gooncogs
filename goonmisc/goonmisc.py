import random
import asyncio
import discord
import os.path
from github import Github
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path, bundled_data_path
from concurrent.futures.thread import ThreadPoolExecutor
from typing import *
import requests
from collections import defaultdict
import datetime
import re
import bisect
import PIL
import io
import aiohttp
import colorsys

class GoonMisc(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=11530251279432)
        self.config.register_global(
                repository=None,

            )
        self.CONTRIB_PATH = cog_data_path(self) / "contributors.txt"
        self.reload_contrib()
        self.is_dad = False

    def reload_contrib(self):
        self.total = 0
        self.contributors = []
        if os.path.exists(self.CONTRIB_PATH):
            for line in open(self.CONTRIB_PATH):
                who, how_much = line.split(': ')
                how_much = int(how_much)
                self.total += how_much
                self.contributors.append((who, how_much))

    def _rebuild_wheel(self, token, repo):
        g = Github(token)
        repo = g.get_repo(repo)
        with open(self.CONTRIB_PATH, 'w') as f:
            for contributor in repo.get_stats_contributors():
                name = contributor.author.name or contributor.author.login
                f.write("{}: {}\n".format(name, contributor.total))

    @commands.command()
    @commands.is_owner()
    async def wheel_set_data(self, ctx: commands.Context, repo: str):
        await self.config.repo.set(repo)
        await ctx.send("Config set")

    @commands.command()
    @commands.is_owner()
    async def rebuild_wheel(self, ctx: commands.Context):
        executor = ThreadPoolExecutor(max_workers=1)
        github_keys = await self.bot.get_shared_api_tokens("github")
        token = None
        if github_keys.get("token") is None:
            return await ctx.send("The GitHub token needs to be set!")
        token = github_keys.get("token")
        await asyncio.get_running_loop().run_in_executor(executor, self._rebuild_wheel,
                token,
                await self.config.repo()
            )
        self.reload_contrib()
        await ctx.send("Wheel of Blame rebuilt (probably)!")

    @commands.command()
    async def blame(self, ctx: commands.Context):
        roll = random.randint(1, self.total)
        for who, how_much in self.contributors:
            roll -= how_much
            if roll <= 0:
                break
        await ctx.send(who)

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def setlogo(self, ctx: commands.Context, logo_url: Optional[str]):
        guild = ctx.guild
        icon = None
        try:
            if logo_url:
                icon = requests.get(logo_url).content
            elif len(ctx.message.attachments) > 0:
                icon = requests.get(ctx.message.attachments[0].url).content
        except Exception:
            await ctx.send("You need to either give a valid URL or attach a valid file!")
            return
        await guild.edit(icon=icon, reason="requested by [ctx.message.author.name]")

    @commands.command()
    async def blastfromthepast(self, ctx: commands.Context):
        channel = ctx.bot.get_channel(383743035894267905) # TODO: unhardcode
        time = datetime.datetime.now()
        time -= datetime.timedelta(days=365)
        async for message in channel.history(limit=1, before=time):
            await ctx.send("> " + "\n> ".join(message.clean_content.split("\n")))

    async def word_react(self, message: discord.Message, word: str):
        emojis = []
        alt_index = defaultdict(int)
        alternatives = {
            # TODO probably remove the custom emoji from here for general purpose usage
            'O': [842117713656545382, '\N{Heavy Large Circle}'],
            'E': [842112367861039115],
            '?': "\N{Black Question Mark Ornament}\N{White Question Mark Ornament}",
            '!': "????????????",
            'A': '????',
            'B': '????',
            '$': '????????????????????',
            'C': '????????',
            'R': '??',
            'X': '?????????',
            'M': '???????????????',
            'H': '???????',
            'P': '????',
            '+': ['???', '????????'],
            '-': '???',
            '8': '????',
            'I': '???',
            'S': '???????',
            'T': '??????',
            'D': '??????',
            'V': '???',
            '1': '????',
            '2': '????',
            '3': '????',

        }
        word = word.upper().replace(' ', '')
        replacements = [
                ('OK', "????"),
                ('!?', "???"),
                ('!!', "???"),
                ('COOL', "????"),
                ('ID', "????"),
                ('VS', "????"),
                ('CL', "????"),
                ('SOS', "????"),
                ('100', "????"),
                ('UP', "????"),
                ('NG', "????"),
                ('NEW', "????"),
                ('FREE', "????"),
                ('10', "????"),
                ('ABCD', "????"),
                ('ABC', "????"),
                ('AB', "????"),
                ('ATM', "????"),
                ('TM', "???"),
                ('WC', "????"),
                ('18', "????"),
                ('1234', "????"),
                ('ZZZ', "????"),
                ('777', "\N{slot machine}"),
                ('69', "??????"),

        ]
        split = re.split(r"(<.*?>)", word)
        for part in split:
            if not part:
                continue
            if part[0] == '<':
                match = re.match(r"<a?:.+?:([0-9]+?)>", part)
                if match:
                    id = int(match.group(1))
                    emoji = self.bot.get_emoji(id)
                    if emoji:
                        emojis.append(emoji)
                continue
            for from_repl, to_repl in replacements:
                if from_repl in part:
                    part = part.replace(from_repl, to_repl, 1)
                    replacements.remove((from_repl, to_repl))
            for letter in part:
                added = False
                if alt_index[letter] == 0:
                    added = True
                    if letter.isalpha():
                        emojis.append(chr(ord("\N{REGIONAL INDICATOR SYMBOL LETTER A}") + ord(letter) - ord('A')))
                    elif letter.isdigit() or letter in '#*':
                        emojis.append(letter + "\N{COMBINING ENCLOSING KEYCAP}")
                    elif letter in "?!+-$":
                        added = False
                    elif letter != " ":
                        emojis.append(letter)
                    alt_index[letter] += 1
                if not added and letter in alternatives:
                    alternative = None
                    while alternative is None and len(alternatives[letter]) >= alt_index[letter]:
                        alternative = alternatives[letter][alt_index[letter] - 1]
                        if isinstance(alternative, int):
                            alternative = self.bot.get_emoji(alternative)
                        alt_index[letter] += 1
                    if alternative:
                        emojis.append(alternative)
        # emojis = emojis[:19]
        for emoji in emojis:
            if emoji is None:
                continue
            try:
                await message.add_reaction(emoji)
            except discord.errors.HTTPException: # not a valid emoji
                pass

    @commands.command()
    async def test_react(self, ctx: commands.Context, *, text: str):
        await self.word_react(ctx.message, text)

    @checks.admin()
    @commands.command()
    async def react_to_message(self, ctx: commands.Context, message: discord.Message, *, text: str):
        await self.word_react(message, text)
        await ctx.message.add_reaction('\N{White Heavy Check Mark}')

    @checks.admin()
    @commands.command()
    async def toggle_dad(self, ctx: commands.Context):
        self.is_dad = not self.is_dad
        await ctx.send("I'm now a dad." if self.is_dad else "I'm no long a dad.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        words = message.clean_content.split()
        if len(words) == 2 and words[1] == 'below' and random.randint(1, 100) == 1:
            await message.channel.send("I'm " + words[0])
        
        # TODO: unhardcode
        if message.channel.id == 298827721604071425 and len(words) > 1 and words[-1].lower().strip("?.!") in ["when", "whence"]:
            msg = "when you code it"
            if random.randint(1, 100) == 1:
                msg = "never"
            elif random.randint(1, 100) == 1:
                msg = f"when {random.choose('pali', 'zewaka', 'mbc', 'flourish', 'yass', 'sov')} codes it"
            await self.word_react(message, msg)

        if random.randint(1, 20) == 1 and re.match(r".*\b69\b.*", message.clean_content):
            await self.word_react(message, "nice")

        if self.is_dad:
            match = re.match(r"^I'm ([a-zA-Z]*).?$", message.clean_content)
            if match:
                await message.channel.send(f"Hi {match.group(1)}, I'm dad")

    @commands.command()
    @checks.admin()
    async def anontalk(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        """Admin command to send a message to a channel through the bot without identifying yourself."""
        await channel.send("\N{LARGE RED SQUARE} __admin message__ \N{LARGE RED SQUARE}\n" + message)

    def _pretty_paint(self, img, from_col, to_col):
        from_hsv = colorsys.rgb_to_hsv(*from_col)
        to_hsv = colorsys.rgb_to_hsv(*to_col)
        def transform(p):
            r, g, b, a = p
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            h += to_hsv[0] - from_hsv[0]
            s *= to_hsv[1] / from_hsv[1]
            v *= to_hsv[2] / from_hsv[2]
            ro, go, bo = colorsys.hsv_to_rgb(h, s, v)
            return (int(ro * 255), int(go * 255), int(bo * 255), a)
        img.putdata(list(map(transform, img.convert('RGBA').getdata())))

    @commands.command()
    @commands.cooldown(1, 1)
    @commands.max_concurrency(1, wait=True)
    async def makelogo(self, ctx: commands.Context,
            background: Optional[Union[discord.Member, discord.PartialEmoji, str]],
            foreground: Optional[Union[discord.Member, discord.PartialEmoji, str]]):
        """
        Creates a variant of the Goonstation logo with given background and foreground.
        Both background and foreground can be entered either as colours (word or #rrggbb) or as URLs to images or as attachments to the message or as custom emoji or as usernames.
        """

        datapath = bundled_data_path(self)
        bg = PIL.Image.open(datapath / "logo_bg.png").convert('RGBA')
        fg = PIL.Image.open(datapath / "logo_g.png").convert('RGBA')

        async def make_paint(arg, attachment_index):
            img_bytes = None
            if len(ctx.message.attachments) > attachment_index:
                arg = ctx.message.attachments[attachment_index].url
            if arg is None:
                return None
            elif isinstance(arg, discord.Member):
                img_bytes = await arg.avatar_url_as(format='png').read()
            elif isinstance(arg, discord.PartialEmoji):
                img_bytes = await arg.url_as(format='png').read()
            elif ord(arg[0]) > 127:
                arg = "https://twemoji.maxcdn.com/v/latest/72x72/{}.png".format('-'.join("{cp:x}".format(cp=ord(c)) for c in arg))
            elif arg and '.' not in arg:
                return PIL.Image.new('RGBA', bg.size, color=arg)
            if arg is None and img_bytes is None:
                return None
            if img_bytes is None:
                async with aiohttp.ClientSession() as session:
                    async with session.get(arg) as response:
                        img_bytes = await response.read()
            image = PIL.Image.open(io.BytesIO(img_bytes))
            scale_factors = [bsize / isize for bsize, isize in zip(bg.size, image.size)]
            scale_factor = max(scale_factors)
            if scale_factor != 1.:
                image = image.resize((int(s * scale_factor) for s in image.size), PIL.Image.BICUBIC)
            if image.size[0] != image.size[1]:
                half_new_size = min(image.size) / 2
                center_x = image.size[0] / 2
                center_y = image.size[1] / 2
                image = image.crop((
                    int(center_x - half_new_size),
                    int(center_y - half_new_size),
                    int(center_x + half_new_size),
                    int(center_y + half_new_size)
                    ))
            return image

        bg_color = None
        if isinstance(background, str) and len(background) > 0 and background[0] == '!':
            try:
                bg_color = PIL.ImageColor.getrgb(background[1:])
            except ValueError:
                pass
        if bg_color is not None:
            bg = PIL.Image.open(datapath / "logo_bg_color.png")
            executor = ThreadPoolExecutor(max_workers=1)
            async with ctx.typing():
                await asyncio.get_running_loop().run_in_executor(executor, self._pretty_paint,
                        bg,
                        PIL.ImageColor.getrgb("#eced42"),
                        bg_color
                    )
        else:
            try:
                bg_paint = await make_paint(background, 0)
            except ValueError:
                return await ctx.send(f"Unknown background color {background}.")
            except PIL.UnidentifiedImageError:
                return await ctx.send(f"Cannot read background image.")
            if bg_paint:
                bg = PIL.ImageChops.multiply(bg, bg_paint.convert('RGBA'))
            else:
                return await ctx.send("You need to provide either a colour or a picture (either as an URL or as an attachment or as a custom emoji or as a username).")

        try:
            fg_paint = await make_paint(background if len(ctx.message.attachments) > 0 else foreground, 1)
        except ValueError:
            return await ctx.send(f"Unknown foreground color {foreground}.")
        except PIL.UnidentifiedImageError:
            return await ctx.send(f"Cannot read foreground image.")
        if fg_paint:
            fg = PIL.ImageChops.multiply(fg, fg_paint.convert('RGBA'))

        bg.paste(fg, (0, 0), fg)

        img_data = io.BytesIO()
        bg.save(img_data, format='png')
        img_data.seek(0)
        img_file = discord.File(img_data, filename="logo.png")
        await ctx.send(file=img_file)


