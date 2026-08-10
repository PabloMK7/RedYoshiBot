from __future__ import annotations

from io import BytesIO

import discord
from PIL import Image, UnidentifiedImageError
from collections.abc import Awaitable, Callable
import re

import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Awaitable, Callable

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont

import math
from collections import defaultdict

from textwrap import wrap


async def on_photo_channel_message(
    message: discord.Message,
    targetChannel: discord.TextChannel
):
    if not message.attachments:
        return False

    for attachment in message.attachments:
        if not attachment.filename.lower().endswith(".bmp") or attachment.size != 0x46536:
            continue

        file_data = BytesIO()
        await attachment.save(file_data)
        file_data.seek(0)

        try:
            img = Image.open(file_data)

            # Verify it's actually a BMP.
            if img.format != "BMP":
                continue

            # Verify dimensions.
            if img.size != (400, 240):
                continue

        except UnidentifiedImageError:
            # Not a valid image.
            continue

        # Save image as PNG
        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)

        discord_file = discord.File(
            output,
            filename="photo.png"
        )

        if len(message.content) > 0:
            title = message.author.display_name.replace("`", "") + ": " + message.content.replace("@", "(at)").replace("`", "'")
        else:
            title = message.author.display_name.replace("`", "") + ": Untitled"

        embed = discord.Embed(
            title=title,
            color=discord.Color.red(),
        )
        embed.set_image(url="attachment://photo.png")
        embed.description = message.jump_url

        msg: discord.Message = await targetChannel.send(
            embed=embed,
            file=discord_file
        )

        await msg.add_reaction("⬆️")

        output.seek(0)
        discord_file2 = discord.File(
            output,
            filename="photo.png"
        )

        await message.reply("Your file `" + attachment.filename.replace("`", "") + "` has been submitted.\n\nTitle: `" + title + "`", file=discord_file2)

        return True

    return False

JUMP_URL_RE = re.compile(
    r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)"
)

async def on_photo_submission_delete(message: discord.Message, bot_server):
    if not message.embeds:
        return

    embed = message.embeds[0]

    match = JUMP_URL_RE.fullmatch(embed.description)
    if not match:
        return

    _, channel_id, message_id = map(int, match.groups())

    channel = bot_server.get_channel(channel_id)

    try:
        original = await channel.fetch_message(message_id)
    except discord.NotFound:
        return

    await original.reply(
        "One of the submissions in this message has been declined by a moderator. Please check the photo contest rules in <#1520026680708563025>."
    )

async def process_messages_with_votes(
    channel: discord.TextChannel | discord.Thread,
    vote_threeshold: int,
    callback: Callable[[discord.Message, int], Awaitable[None]],
    less_than_mode: bool,
    vote_emoji: str = "⬆️",
    *,
    limit: int | None = None,
    oldest_first: bool = True,
) -> None:
    async for message in channel.history(
        limit=limit,
        oldest_first=oldest_first,
    ):
        votes = 0

        for reaction in message.reactions:
            if str(reaction.emoji) == vote_emoji:
                votes = reaction.count
                break

        if less_than_mode:
            if votes < vote_threeshold:
                await callback(message, votes)
        else:
            if votes > vote_threeshold:
                await callback(message, votes)

# (winner_message_id, loser_message_id, voter_user_id) -> None
VoteCallback = Callable[[int, int, int], Awaitable[None]]

@dataclass(frozen=True)
class SubmissionEntry:
    message_id: int
    jump_url: str
    bot_jump_url: str
    image_url: str
    image_title: str
    submitter_id: int


async def _resolve_submitter_id(
    bot: discord.Client, jump_url: str
) -> int | None:
    match = JUMP_URL_RE.fullmatch(jump_url)
    if not match:
        return None
    guild_id, channel_id, message_id = (int(g) for g in match.groups())
    try:
        guild = bot.get_guild(guild_id)
        if guild is None:
            return None
        channel = guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
        original = await channel.fetch_message(message_id)
        return original.author.id
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def fetch_submission_pool(
    bot: discord.Client,
    channel: discord.TextChannel | discord.Thread,
    include_submitter: bool,
    limit: int | None = 1000,
) -> list[SubmissionEntry]:
    pool: list[SubmissionEntry] = []
    async for message in channel.history(limit=limit):
        if not message.embeds:
            continue
        embed = message.embeds[0]
        if not embed.description or not JUMP_URL_RE.fullmatch(embed.description):
            continue
        if embed.image is None or not embed.image.url:
            continue
        submitter_id = None if not include_submitter else await _resolve_submitter_id(bot, embed.description)
        pool.append(
            SubmissionEntry(
                message_id=message.id,
                jump_url=embed.description,
                bot_jump_url=message.jump_url,
                image_url=embed.image.url,
                image_title=embed.title,
                submitter_id=submitter_id,  # new field on SubmissionEntry
            )
        )
    return pool

async def _load_deduped_votes(database, pool: list[SubmissionEntry]) -> list[tuple[int, int]]:
    submitter_by_id = {e.message_id: e.submitter_id for e in pool}
    pool_ids = set(submitter_by_id)

    latest: dict[tuple[int, frozenset[int]], tuple[int, int]] = {}
    entries = await database.get_votes_photo_contest()
    for winner_id, loser_id, voter_id in entries:
        if winner_id not in pool_ids or loser_id not in pool_ids:
            continue
        if voter_id in (submitter_by_id[winner_id], submitter_by_id[loser_id]):
            continue  # self-vote on either entry in the pair
        key = (voter_id, frozenset((winner_id, loser_id)))
        latest[key] = (winner_id, loser_id)
    return list(latest.values())

_ANCHOR_ID = -1
_ANCHOR_STRENGTH = 1.0

def bradley_terry_scores(
    item_ids: set[int],
    votes: list[tuple[int, int]],
    iterations: int = 200,
    tol: float = 1e-9,
) -> dict[int, float]:
    wins: dict[int, float] = defaultdict(float)
    games: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))

    for winner, loser in votes:
        if winner == loser:
            continue
        wins[winner] += 1
        games[winner][loser] += 1
        games[loser][winner] += 1

    active_ids = [i for i in item_ids if sum(games[i].values()) > 0]
    if not active_ids:
        return {}

    for i in active_ids:
        wins[i] += 1    # virtual win vs anchor
        games[i][_ANCHOR_ID] += 2   # one win + one loss vs anchor

    strength = {i: 1.0 for i in active_ids}

    for _ in range(iterations):
        new_strength = {}
        for i in active_ids:
            denom = 0.0
            for j, n_ij in games[i].items():
                opp = _ANCHOR_STRENGTH if j == _ANCHOR_ID else strength.get(j)
                if opp is None:
                    continue
                denom += n_ij / (strength[i] + opp)
            new_strength[i] = wins[i] / denom if denom > 0 else strength[i]

        max_delta = max(abs(new_strength[i] - strength[i]) for i in active_ids)
        strength = new_strength
        if max_delta < tol:
            break

    return {i: math.log(s) for i, s in strength.items()}


async def rank_photo_contest(
    bot,
    database,
    channel: discord.TextChannel | discord.Thread,
    top_n: int = 10,
    limit: int | None = 1000,
) -> list[tuple[SubmissionEntry, float | None]]:
    print("Fetching submission pool")
    pool = await fetch_submission_pool(bot, channel, True, limit=limit)
    print("Got {} entries".format(len(pool)))
    pool_ids = {entry.message_id for entry in pool}

    print("Calculating scores")
    votes = await _load_deduped_votes(database, pool)
    scores = bradley_terry_scores(pool_ids, votes)

    ranked: list[tuple[SubmissionEntry, float]] = []
    unranked: list[tuple[SubmissionEntry, None]] = []
    for entry in pool:
        if entry.message_id in scores:
            ranked.append((entry, scores[entry.message_id]))
        else:
            unranked.append((entry, None))

    ranked.sort(key=lambda pair: pair[1], reverse=True)

    res = (ranked + unranked)

    print("Returning {} scores".format(min(top_n, len(res))))

    return res[:min(top_n, len(res))]


async def _download(session: aiohttp.ClientSession, url: str) -> bytes:
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.read()

async def _build_matchup_image(
    session: aiohttp.ClientSession, a: SubmissionEntry, b: SubmissionEntry
) -> discord.File:
    from io import BytesIO

    bytes_a = await _download(session, a.image_url)
    bytes_b = await _download(session, b.image_url)

    img_a = Image.open(BytesIO(bytes_a)).convert("RGB")
    img_b = Image.open(BytesIO(bytes_b)).convert("RGB")

    gap = 24
    padding = 10

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
    except OSError:
        font = ImageFont.load_default()

    width = max(img_a.width, img_b.width)

    # Temporary draw object for measuring text
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def wrap_text(text: str) -> list[str]:
        words = text.split()
        lines = []
        current = []

        for word in words:
            test = " ".join(current + [word])
            text_width = measure.textbbox((0, 0), test, font=font)[2]
            if text_width <= width - 2 * padding:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]

        if current:
            lines.append(" ".join(current))

        return lines

    top_lines = wrap_text(a.image_title)
    bottom_lines = wrap_text(b.image_title)

    line_height = (
        measure.textbbox((0, 0), "Ag", font=font)[3]
        - measure.textbbox((0, 0), "Ag", font=font)[1]
    )

    top_label_h = len(top_lines) * line_height + 20
    bottom_label_h = len(bottom_lines) * line_height + 20

    height = (
        top_label_h
        + img_a.height
        + bottom_label_h
        + img_b.height
    )

    canvas = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(canvas)

    # Draw top title
    draw.multiline_text(
        (width // 2, top_label_h // 2),
        "\n".join(top_lines),
        font=font,
        fill="white",
        anchor="mm",
        align="center",
    )

    # Paste top image
    y = top_label_h
    canvas.paste(img_a, ((width - img_a.width) // 2, y))

    # Draw bottom title
    y += img_a.height
    draw.multiline_text(
        (width // 2, y + bottom_label_h // 2),
        "\n".join(bottom_lines),
        font=font,
        fill="white",
        anchor="mm",
        align="center",
    )

    # Paste bottom image
    y += bottom_label_h
    canvas.paste(img_b, ((width - img_b.width) // 2, y))

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    buf.seek(0)

    return discord.File(buf, filename="matchup.png")


class PairwiseVoteView(discord.ui.View):
    def __init__(
        self,
        voter_id: int,
        pool: list[SubmissionEntry],
        on_vote: VoteCallback,
        session: aiohttp.ClientSession,
        *,
        timeout: float = 180,
    ):
        super().__init__(timeout=timeout)
        self.voter_id = voter_id
        self.pool = pool
        self.on_vote = on_vote
        self.session = session
        self.message: discord.Message | None = None
        self.entry_a: SubmissionEntry | None = None
        self.entry_b: SubmissionEntry | None = None
        self._last_pair: tuple[int, int] | None = None
        self.total_votes = 1
        self.max_votes = 10
        self._draw_pair()

    def _draw_pair(self) -> bool:
        if len(self.pool) < 2:
            return False

        a, b = random.sample(self.pool, 2)
        for _ in range(10):
            key = tuple(sorted((a.message_id, b.message_id)))
            if key != self._last_pair:
                break
            a, b = random.sample(self.pool, 2)

        self.entry_a, self.entry_b = a, b
        self._last_pair = tuple(sorted((a.message_id, b.message_id)))
        return True

    async def render(self) -> tuple[discord.Embed, discord.File]:
        file = await _build_matchup_image(self.session, self.entry_a, self.entry_b)
        embed = discord.Embed(
            title="Which photo do you prefer?",
            description="Vote **Top** or **Bottom** (you can stop voting at any time).\n\n**Votes: {}/{}**".format(self.total_votes, self.max_votes),
            color=discord.Color.red(),
        )
        embed.set_image(url="attachment://matchup.png")
        return embed, file

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.voter_id:
            await interaction.response.send_message(
                "This voting session isn't yours, run `/votephoto` to start your own.",
                ephemeral=True,
            )
            return False
        return True

    async def _advance(self, interaction: discord.Interaction) -> None:
        if not self._draw_pair() or self.total_votes > self.max_votes:
            for child in self.children:
                child.disabled = True
            await interaction.edit_original_response(
                content="Thanks for voting!",
                embed=None,
                attachments=[],
                view=None,
            )
            self.stop()
            return

        embed, file = await self.render()
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

    async def _handle_vote(
        self,
        interaction: discord.Interaction,
        winner: SubmissionEntry,
        loser: SubmissionEntry,
    ) -> None:
        await interaction.response.defer()
        self.total_votes += 1
        await self.on_vote(winner.message_id, loser.message_id, interaction.user.id)
        await self._advance(interaction)

    @discord.ui.button(label="Vote Top", style=discord.ButtonStyle.blurple)
    async def vote_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, self.entry_a, self.entry_b)

    @discord.ui.button(label="Vote Bottom", style=discord.ButtonStyle.blurple)
    async def vote_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, self.entry_b, self.entry_a)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self._advance(interaction)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_voting(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
                content="Thanks for voting!",
                embed=None,
                attachments=[],
                view=None,
            )
        self.stop()

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass


class PairwiseVoting():
    def __init__(
        self,
        bot: commands.Bot,
        submissions_channel_id: int,
        on_vote: VoteCallback,
        *,
        refresh_minutes: float = 5,
        history_limit: int | None = 1000,
        vote_command_channel_id: int | None = None,
    ):
        self.bot = bot
        self.submissions_channel_id = submissions_channel_id
        self.on_vote = on_vote
        self.history_limit = history_limit
        # If set, /vote only works when run inside this channel.
        self.vote_command_channel_id = vote_command_channel_id
        self._pool: list[SubmissionEntry] = []
        self._pool_updated_at: datetime | None = None

        self._session = aiohttp.ClientSession()

        self._refresh_pool.change_interval(minutes=refresh_minutes)
        self._refresh_pool.start()

    @tasks.loop(minutes=5)
    async def _refresh_pool(self) -> None:
        channel = self.bot.get_channel(self.submissions_channel_id)
        if channel is None:
            return
        self._pool = await fetch_submission_pool(self.bot, channel, False, limit=self.history_limit)
        self._pool_updated_at = datetime.now(timezone.utc)

    @_refresh_pool.before_loop
    async def _before_refresh(self) -> None:
        await self.bot.wait_until_ready()

    async def _get_pool(self) -> list[SubmissionEntry]:
        # Fall back to a live fetch if the background task hasn't caught up yet.
        stale = self._pool_updated_at is None or (
            datetime.now(timezone.utc) - self._pool_updated_at > timedelta(minutes=30)
        )
        if stale:
            channel = self.bot.get_channel(self.submissions_channel_id)
            if channel is not None:
                self._pool = await fetch_submission_pool(self.bot, channel, False, limit=self.history_limit)
                self._pool_updated_at = datetime.now(timezone.utc)
        return self._pool

    async def start_vote(self, interaction: discord.Interaction) -> None:
        if (
            self.vote_command_channel_id is not None
            and interaction.channel_id != self.vote_command_channel_id
        ):
            await interaction.response.send_message(
                f"This command can only be used in <#{self.vote_command_channel_id}>.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        pool = await self._get_pool()
        if len(pool) < 2:
            await interaction.followup.send("Not enough submissions to vote on yet.", ephemeral=True)
            return

        view = PairwiseVoteView(interaction.user.id, pool, self.on_vote, self._session)
        embed, file = await view.render()
        message = await interaction.followup.send(
            embed=embed, file=file, view=view, ephemeral=True, wait=True
        )
        view.message = message

class StartVoteView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Start Vote", style=discord.ButtonStyle.primary)
    async def vote_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.cog.start_vote(interaction)