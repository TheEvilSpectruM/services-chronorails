import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

RESULT_CHANNEL_ID = 1359893180014792724  # Salon où poster les résultats
GUILD_ID = 123456789012345678  # Remplace par ton serveur pour test

# Vérification rôle Staff 🛡️ ou Responsable réseau
def is_staff_or_responsable():
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed_role_ids = {1345857319585714316, 1361714714010189914}
        member = interaction.user
        if isinstance(member, discord.Member):
            if any(role.id in allowed_role_ids for role in member.roles):
                return True
        await interaction.response.send_message("⛔ Vous devez être Staff 🛡️ ou Responsable réseau pour utiliser cette commande.", ephemeral=True)
        return False
    return discord.app_commands.check(predicate)

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Commands synced: {len(synced)}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")

# Serveur web pour health check Koyeb
async def handle(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def run_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

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

@bot.tree.command(
    name="resultats",
    description="Envoyer les résultats d'une formation à un utilisateur",
    guild=discord.Object(id=GUILD_ID)
)
@is_staff_or_responsable()
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
    channel = bot.get_channel(RESULT_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Le salon de résultats n'a pas été trouvé.", ephemeral=True)
        return

    status_text = "passé" if passe.value == "oui" else "pas passé"
    bravo = " 🎉 BRAVO !" if passe.value == "oui" else ""

    message = f"{user.mention}, vous avez {status_text} la formation de **{formation.value}**.{bravo}"

    await channel.send(message)
    await interaction.response.send_message(f"Résultat envoyé dans {channel.mention}", ephemeral=True)

async def main():
    await run_webserver()
    token = os.getenv("TOKEN")
    if not token:
        print("Erreur : la variable d'environnement TOKEN est manquante !")
        return
    await bot.start(token)

asyncio.run(main())
