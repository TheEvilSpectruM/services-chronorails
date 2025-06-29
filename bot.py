import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

RESULT_CHANNEL_ID = 1359893180014792724  # Salon résultats
TRAFFIC_CHANNEL_ID = 1379137936796291224  # Salon trafic

ROLE_IDS_ALLOWED = [1345857319585714316, 1361714714010189914]  # Staff 🛡️ et Responsable réseau

# Statuts trafic avec emoji
STATUTS = {
    "opérationnel": "🟢",
    "accident": "🚧",
    "fermée travaux": "🔨",
    "trafic important": "⚠️",
    "fermée accident": "⛔"
}

# Statuts initiaux des lignes
status_lignes = {
    "Ligne 8": "opérationnel",
    "Ligne 3Bis": "opérationnel",
    "Ligne 6": "opérationnel"
}

TRAFFIC_MESSAGE_ID = None  # ID message embed trafic

# Serveur web pour health check
async def handle(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def run_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

def build_embed():
    embed = discord.Embed(title="INFO TRAFFIC - CHRONORAILS", color=discord.Color.blue())
    for ligne, statut in status_lignes.items():
        emoji = STATUTS.get(statut, "❔")
        embed.add_field(name=ligne, value=f"{emoji} {statut.capitalize()}", inline=False)
    return embed

async def create_or_fetch_message():
    channel = bot.get_channel(TRAFFIC_CHANNEL_ID)
    if channel is None:
        print("Salon trafic introuvable")
        return None

    async for message in channel.history(limit=100):
        if message.author == bot.user and message.embeds:
            print("Message embed trafic récupéré")
            return message

    embed = build_embed()
    msg = await channel.send(embed=embed)
    await msg.pin()
    print("Message embed trafic créé et épinglé")
    return msg

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    global TRAFFIC_MESSAGE_ID
    msg = await create_or_fetch_message()
    if msg:
        TRAFFIC_MESSAGE_ID = msg.id
        print(f"Message trafic prêt : {TRAFFIC_MESSAGE_ID}")
    try:
        synced = await bot.tree.sync()
        print(f"Commands synced: {len(synced)}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")

# --- Commande /statut ---
@bot.tree.command(name="statut", description="Affiche le statut actuel du bot")
async def statut(interaction: discord.Interaction):
    status = bot.status
    if status == discord.Status.online:
        emoji = "🟢"
        texte = "En ligne"
    elif status == discord.Status.idle:
        emoji = "🟡"
        texte = "Problèmes mineurs"
    elif status == discord.Status.offline or status == discord.Status.invisible:
        emoji = "🔴"
        texte = "Hors Ligne"
    else:
        emoji = "❔"
        texte = "Statut inconnu"
    
    await interaction.response.send_message(f"Statut du bot : {emoji} {texte}")

# --- Commande /resultats ---
@bot.tree.command(
    name="resultats",
    description="Envoyer les résultats d'une formation à un utilisateur"
)
@discord.app_commands.describe(
    user="Utilisateur concerné",
    formation="Formation concernée",
    passe="A-t-il passé la formation ?"
)
@discord.app_commands.choices(formation=[
    discord.app_commands.Choice(name="Staff", value="Staff"),
    discord.app_commands.Choice(name="Conducteur [CM]", value="Conducteur [CM]"),
    discord.app_commands.Choice(name="PCC", value="PCC"),
])
@discord.app_commands.choices(passe=[
    discord.app_commands.Choice(name="Oui", value="oui"),
    discord.app_commands.Choice(name="Non", value="non"),
])
async def resultats(interaction: discord.Interaction, user: discord.Member, formation: discord.app_commands.Choice[str], passe: discord.app_commands.Choice[str]):
    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.response.send_message("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
        return

    if not any(role.id in ROLE_IDS_ALLOWED for role in member.roles):
        await interaction.response.send_message("⛔ Vous n'avez pas le rôle requis pour utiliser cette commande.", ephemeral=True)
        return

    channel = bot.get_channel(RESULT_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Le salon de résultats n'a pas été trouvé.", ephemeral=True)
        return

    status_text = "passé" if passe.value == "oui" else "pas passé"
    bravo = " 🎉 BRAVO !" if passe.value == "oui" else ""

    message = f"{user.mention}, vous avez {status_text} la formation de **{formation.value}**.{bravo}"

    await channel.send(message)
    await interaction.response.send_message(f"Résultat envoyé dans {channel.mention}", ephemeral=True)

# --- Commande /postuler ---
@bot.tree.command(
    name="postuler",
    description="Obtenir le lien pour postuler à une formation"
)
@app_commands.describe(
    formation="Choisissez une formation"
)
@app_commands.choices(formation=[
    app_commands.Choice(name="Staff", value="Staff"),
    app_commands.Choice(name="Conducteur [CM]", value="Conducteur [CM]"),
    app_commands.Choice(name="PCC", value="PCC"),
])
async def postuler(interaction: discord.Interaction, formation: app_commands.Choice[str]):
    liens = {
        "PCC": "https://docs.google.com/forms/d/1lCdDmKSKl6uN68oh0IMRnJwtgJE7bZMSSu9kA7xTXYw/viewform?edit_requested=true",
        "Conducteur [CM]": "https://docs.google.com/forms/d/e/1FAIpQLSe2rxLd7w-rrPtPxxwvOAhDC7YD0J8II-YJn_MEyKhSg0csyQ/viewform?usp=header",
        "Staff": "https://docs.google.com/forms/d/1dkl-CJNiUlesD7sSDLJKw0HokJE8zLIrcN4GwD0nGqo/viewform?edit_requested=true"
    }
    lien = liens.get(formation.value)
    await interaction.response.send_message(
        f"Clique [ici]({lien}) pour postuler au rôle de **{formation.value}**.",
        ephemeral=True
    )

# --- Check rôle Staff/RR pour /traffic ---
def is_staff_or_rr():
    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Commande à utiliser en serveur uniquement.", ephemeral=True)
            return False
        if any(role.id in ROLE_IDS_ALLOWED for role in member.roles):
            return True
        await interaction.response.send_message("⛔ Vous devez être Staff ou Responsable réseau pour utiliser cette commande.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- Commande /traffic ---
@bot.tree.command(name="traffic", description="Met à jour le statut de trafic d'une ligne")
@is_staff_or_rr()
@app_commands.describe(
    ligne="Choisissez la ligne",
    probleme="Choisissez le problème"
)
@app_commands.choices(ligne=[
    app_commands.Choice(name="Ligne 8", value="Ligne 8"),
    app_commands.Choice(name="Ligne 3Bis", value="Ligne 3Bis"),
    app_commands.Choice(name="Ligne 6", value="Ligne 6"),
])
@app_commands.choices(probleme=[
    app_commands.Choice(name="Opérationnel", value="opérationnel"),
    app_commands.Choice(name="Accident sur la ligne", value="accident"),
    app_commands.Choice(name="Fermée pour travaux", value="fermée travaux"),
    app_commands.Choice(name="Trafic important", value="trafic important"),
    app_commands.Choice(name="Fermée pour accident", value="fermée accident"),
])
async def traffic(interaction: discord.Interaction, ligne: app_commands.Choice[str], probleme: app_commands.Choice[str]):
    global status_lignes, TRAFFIC_MESSAGE_ID

    # Met à jour le statut
    status_lignes[ligne.value] = probleme.value

    channel = bot.get_channel(TRAFFIC_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Le salon de trafic n'a pas été trouvé.", ephemeral=True)
        return

    if TRAFFIC_MESSAGE_ID is None:
        await interaction.response.send_message("Le message de trafic n'a pas encore été initialisé.", ephemeral=True)
        return

    try:
        msg = await channel.fetch_message(TRAFFIC_MESSAGE_ID)
    except:
        await interaction.response.send_message("Impossible de récupérer le message de trafic.", ephemeral=True)
        return

    embed = build_embed()
    await msg.edit(embed=embed)

    await interaction.response.send_message(f"Le statut de **{ligne.value}** a été mis à jour à **{probleme.name}** {STATUTS.get(probleme.value, '')}.", ephemeral=True)

async def main():
    await run_webserver()
    token = os.getenv("TOKEN")
    if not token:
        print("Erreur : la variable d'environnement TOKEN est manquante !")
        return
    await bot.start(token)

asyncio.run(main())
