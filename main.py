import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
import shutil
from datetime import datetime
from dotenv import load_dotenv
from keep_alive import keep_alive  # Importa il server Flask

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

AUTORIZZATI = ["1109770445953183844"]
RUOLI_AUTORIZZATI = ["🔮Manager🔮", "⚜️Head-Admin⚜️", "🚨Retarder🚨", "♦️Staff♦️"]

# Imposta l'ID del canale dove vuoi ricevere i backup
BACKUP_CHANNEL_ID = 1441739226575011881  # <-- sostituisci con l'ID del tuo canale staff

async def crea_backup_giornaliero():
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"backup_xp_{timestamp}.json"
    try:
        shutil.copy("xp_data.json", filename)
        print(f"🟡 Backup creato: {filename}")
        channel = bot.get_channel(BACKUP_CHANNEL_ID)
        if channel:
            await channel.send(file=discord.File(filename))
    except Exception as e:
        print(f"❌ Errore nel backup: {e}")



def autorizzato(interaction):
    return (
        str(interaction.user.id) in AUTORIZZATI or
        any(role.name in RUOLI_AUTORIZZATI for role in interaction.user.roles)
    )

@bot.event
async def on_ready():
    print(f"🟢 Bot avviato come {bot.user}")
    await tree.sync()
    bot.loop.create_task(xp_vocale_loop())
    bot.loop.create_task(backup_giornaliero_loop())

async def backup_giornaliero_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await crea_backup_giornaliero()
        await asyncio.sleep(60)  # per test ogni minuto


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

    data.setdefault(server_id, {}).setdefault(user_id, {})
    data[server_id][user_id].setdefault("text_xp", 0)
    data[server_id][user_id].setdefault("voice_xp", 0)

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

                    data.setdefault(server_id, {}).setdefault(user_id, {})
                    data[server_id][user_id].setdefault("text_xp", 0)
                    data[server_id][user_id].setdefault("voice_xp", 0)

                    data[server_id][user_id]["voice_xp"] += 10

                    with open("xp_data.json", "w") as f:
                        json.dump(data, f, indent=4)

        await asyncio.sleep(120)

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

    await interaction.response.send_message(
        f"✅ Hai aggiunto {quantità} XP **{tipo}** a {membro.mention}."
    )
@tree.command(name="rimuovixp", description="Rimuove XP da un utente (solo admin)")
@app_commands.describe(membro="Utente", tipo="testo o voce", quantità="XP da rimuovere")
async def rimuovixp(interaction: discord.Interaction, membro: discord.Member, tipo: str, quantità: int):
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
        data[server_id][user_id]["text_xp"] = max(data[server_id][user_id]["text_xp"] - quantità, 0)
    else:
        data[server_id][user_id]["voice_xp"] = max(data[server_id][user_id]["voice_xp"] - quantità, 0)

    with open("xp_data.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(
        f"🔻 Hai rimosso {quantità} XP **{tipo}** da {membro.mention}.", ephemeral=True
    )

@tree.command(name="resetxp", description="Resetta XP di un utente o di tutti (solo admin)")
@app_commands.describe(membro="Utente da resettare (opzionale)")
async def resetxp(interaction: discord.Interaction, membro: discord.Member = None):
    if not autorizzato(interaction):
        await interaction.response.send_message("⛔ Non hai il permesso per usare questo comando.", ephemeral=True)
        return

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    server_id = str(interaction.guild.id)

    if membro:
        user_id = str(membro.id)
        data.setdefault(server_id, {})[user_id] = {"text_xp": 0, "voice_xp": 0}
        msg = f"🔄 XP di {membro.mention} resettato."
    else:
        data[server_id] = {}
        msg = "🔄 XP di tutti gli utenti resettato."

    with open("xp_data.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="xpvoce", description="Mostra XP vocale dell'utente")
async def xpvoce(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    server_id = str(interaction.guild.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    voice_xp = data.get(server_id, {}).get(user_id, {}).get("voice_xp", 0)
    await interaction.response.send_message(f"🎙️ Hai guadagnato **{voice_xp} XP vocale**.", ephemeral=True)

@tree.command(name="xptesto", description="Mostra XP testuale dell'utente")
async def xptesto(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    server_id = str(interaction.guild.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    text_xp = data.get(server_id, {}).get(user_id, {}).get("text_xp", 0)
    await interaction.response.send_message(f"💬 Hai guadagnato **{text_xp} XP testuale**.", ephemeral=True)

@tree.command(name="backupxp", description="Crea un backup manuale del file XP (solo admin)")
async def backupxp(interaction: discord.Interaction):
    if not autorizzato(interaction):
        await interaction.response.send_message("⛔ Non hai il permesso per usare questo comando.", ephemeral=True)
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_xp_{timestamp}.json"
    try:
        shutil.copy("xp_data.json", filename)
        await interaction.response.send_message(f"🗂️ Backup creato: `{filename}`", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Errore nel backup: {e}", ephemeral=True)

@tree.command(name="ripristinaxp", description="Ripristina XP da un file di backup (solo admin)")
@app_commands.describe(nome_file="Nome del file di backup (es. backup_xp_20251023.json)")
async def ripristinaxp(interaction: discord.Interaction, nome_file: str):
    if not autorizzato(interaction):
        await interaction.response.send_message("⛔ Non hai il permesso per usare questo comando.", ephemeral=True)
        return

    try:
        with open(nome_file, "r") as f:
            dati_backup = json.load(f)
        with open("xp_data.json", "w") as f:
            json.dump(dati_backup, f, indent=4)
        await interaction.response.send_message(f"✅ XP ripristinato da `{nome_file}`.", ephemeral=True)
    except FileNotFoundError:
        await interaction.response.send_message(f"❌ Il file `{nome_file}` non esiste.", ephemeral=True)
    except json.JSONDecodeError:
        await interaction.response.send_message(f"⚠️ Il file `{nome_file}` non è valido o è corrotto.", ephemeral=True)

# 🔥 Avvia il server Flask e il bot Discord
keep_alive()
bot.run(TOKEN)






