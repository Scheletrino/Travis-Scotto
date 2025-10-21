import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import shutil
from datetime import datetime
from dotenv import load_dotenv
import glob

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

AUTORIZZATI = ["1109770445953183844"]  # ← tuo ID
RUOLI_AUTORIZZATI = ["🔮Manager🔮", "⚜️Head-Admin⚜️", "🚨Retarder🚨", "♦️Staff♦️"]

def crea_backup_giornaliero():
    timestamp = datetime.now().strftime("%Y%m%d")
    try:
        shutil.copy("xp_data.json", f"backup_xp_{timestamp}.json")
        print(f"📁 Backup creato: backup_xp_{timestamp}.json")
    except Exception as e:
        print(f"❌ Errore nel backup: {e}")

@bot.event
async def on_ready():
    print("✅ Bot avviato come", bot.user)
    await tree.sync()
    bot.loop.create_task(xp_vocale_loop())
    bot.loop.create_task(backup_giornaliero_loop())

async def backup_giornaliero_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        crea_backup_giornaliero()
        await asyncio.sleep(86400)

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    user_id = str(message.author.id)
    server_id = str(message.guild.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault(server_id, {}).setdefault(user_id, {
        "text_xp": 0,
        "voice_xp": 0
    })

    data[server_id][user_id]["text_xp"] += 10

    with open("xp_data.json", "w") as f:
        json.dump(data, f, indent=4)

    await bot.process_commands(message)

async def xp_vocale_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue

                    user_id = str(member.id)
                    server_id = str(guild.id)

                    try:
                        with open("xp_data.json", "r") as f:
                            data = json.load(f)
                    except FileNotFoundError:
                        data = {}

                    data.setdefault(server_id, {}).setdefault(user_id, {
                        "text_xp": 0,
                        "voice_xp": 0
                    })

                    data[server_id][user_id]["voice_xp"] += 10

                    with open("xp_data.json", "w") as f:
                        json.dump(data, f, indent=4)

        await asyncio.sleep(120)

def autorizzato(interaction):
    return (
        str(interaction.user.id) in AUTORIZZATI or
        any(role.name in RUOLI_AUTORIZZATI for role in interaction.user.roles)
    )

@tree.command(name="profilo", description="Mostra il tuo profilo XP")
async def profilo(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    server_id = str(interaction.guild.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    user_data = data.get(server_id, {}).get(user_id, {})
    text_xp = user_data.get("text_xp", 0)
    voice_xp = user_data.get("voice_xp", 0)
    xp = text_xp + voice_xp
    livello = xp // 100
    progresso = xp % 100
    barra = "█" * (progresso // 10) + "░" * (10 - (progresso // 10))

    await interaction.response.send_message(
        f"{interaction.user.mention}, il tuo profilo XP:\n"
        f"> Livello: **{livello}**\n"
        f"> XP Totale: **{xp}** (💬 {text_xp}, 🔊 {voice_xp})\n"
        f"> Progresso: `{barra}` {progresso}/100 XP"
    )

@tree.command(name="classifica", description="Mostra la classifica XP del server")
async def classifica(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        await interaction.response.send_message("⚠️ Nessun dato XP trovato.")
        return

    utenti = data.get(server_id, {})
    classifica = []

    for user_id, xp_data in utenti.items():
        text_xp = xp_data.get("text_xp", 0)
        voice_xp = xp_data.get("voice_xp", 0)
        totale = text_xp + voice_xp
        classifica.append((user_id, totale, text_xp, voice_xp))

    classifica.sort(key=lambda x: x[1], reverse=True)
    top10 = classifica[:10]

    messaggio = "**🏆 Classifica XP del server:**\n"
    for i, (user_id, totale, text_xp, voice_xp) in enumerate(top10, start=1):
        membro = interaction.guild.get_member(int(user_id))
        nome = membro.display_name if membro else f"ID {user_id}"
        messaggio += f"{i}. **{nome}** — {totale} XP (💬 {text_xp}, 🔊 {voice_xp})\n"

    await interaction.response.send_message(messaggio)

@tree.command(name="xp", description="Mostra l'XP totale di un utente")
@app_commands.describe(membro="Utente da controllare")
async def xp(interaction: discord.Interaction, membro: discord.Member):
    user_id = str(membro.id)
    server_id = str(interaction.guild.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    user_data = data.get(server_id, {}).get(user_id, {})
    text_xp = user_data.get("text_xp", 0)
    voice_xp = user_data.get("voice_xp", 0)
    xp = text_xp + voice_xp

    await interaction.response.send_message(
        f"{membro.mention} ha **{xp} XP** totali (💬 {text_xp}, 🔊 {voice_xp})"
    )

@tree.command(name="aggiungixp", description="Aggiunge XP a un utente (solo admin)")
@app_commands.describe(membro="Utente", tipo="testo o voce", quantità="XP da aggiungere")
async def aggiungixp(interaction: discord.Interaction, membro: discord.Member, tipo: str, quantità: int):
    if not autorizzato(interaction):
        await interaction.response.send_message("⛔ Non hai il permesso per usare questo comando.", ephemeral=True)
        return

    if tipo not in ["testo", "voce"]:
        await interaction.response.send_message("⚠️ Tipo XP non valido. Usa 'testo' o 'voce'.", ephemeral=True)
        return

    user_id = str(membro.id)
    server_id = str(interaction.guild.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault(server_id, {}).setdefault(user_id, {
        "text_xp": 0,
        "voice_xp": 0
    })

    if tipo == "testo":
        data[server_id][user_id]["text_xp"] += quantità
    else:
        data[server_id][user_id]["voice_xp"] += quantità

    with open("xp_data.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(f"✅ Hai aggiunto {quantità} XP **{tipo}** a {membro.mention}.")

@tree.command(name="resetxp", description="Azzera l'XP di un utente (solo admin)")
@app_commands.describe(membro="Utente da resettare")
async def resetxp(interaction: discord.Interaction
