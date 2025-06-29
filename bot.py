import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

RESULT_CHANNEL_ID = 1359893180014792724  # Salon où poster les résultats
TRAFFIC_CHANNEL_ID = 1379137936796291224  # Salon de l'embed trafic

ROLE_IDS_ALLOWED = [1345857319585714316, 1361714714010189914]  # Staff 🛡️ et Responsable réseau

FORM_LINKS = {
    "Staff": "https://docs.google.com/forms/d/1dkl-CJNiUlesD7sSDLJKw0HokJE8zLIrcN4GwD0nGqo/viewform?edit_requested=true",
    "Conducteur [CM]": "https://docs.google.com/forms/d/e/1FAIpQLSe2rxLd7w-rrPtPxxwvOAhDC7YD0J8II-YJn_MEyKhSg0csyQ/viewform?usp=header",
    "PCC": "https://docs.google.com/forms/d/1lCdDmKSKl6uN68oh0IMRnJwtgJE7bZMSSu9kA7xTXYw/viewform?edit_requested=true",
}

def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):
            await interaction.response.send_message("Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return False
        if any(role.id in ROLE_IDS_ALLOWED for role in member.roles):
            return True
        await interaction.response.send_message("⛔ Vous devez être Staff ou Responsable réseau pour utiliser cette commande.", ephemeral=True)
        return False
    return discord.app_commands.check(predicate)


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync()
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
    name="postuler",
    description="Obtenir le lien pour postuler à une formation"
)
@discord.app_commands.describe(
    formation="Choisissez une formation"
)
@discord.app_commands.choices(formation=[
    discord.app_commands.Choice(name="Staff", value="Staff"),
    discord.app_commands.Choice(name="Conducteur [CM]", value="Conducteur [CM]"),
    discord.app_commands.Choice(name="PCC", value="PCC"),
])
async def postuler(interaction: discord.Interaction, formation: discord.app_commands.Choice[str]):
    lien = FORM_LINKS.get(formation.value)
    if not lien:
        await interaction.response.send_message("Lien de formulaire introuvable.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"Pour postuler au rôle de **{formation.value}**, cliquez ici : [Cliquez ici]({lien})",
        ephemeral=True
    )


@bot.tree.command(
    name="resultats",
    description="Envoyer les résultats d'une formation à un utilisateur"
)
@is_staff()
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


def create_traffic_embed(statuses=None):
    if statuses is None:
        statuses = {
            "8Bis": "🟢 Opérationnel",
            "3Bis": "🟢 Opérationnel",
            "6": "🟢 Opérationnel"
        }
    embed = discord.Embed(title="INFO TRAFFIC - CHRONORAILS", color=0x1e90ff)
    embed.add_field(name="Ligne 8Bis:", value=statuses.get("8Bis", "🟢 Opérationnel"), inline=False)
    embed.add_field(name="Ligne 3Bis:", value=statuses.get("3Bis", "🟢 Opérationnel"), inline=False)
    embed.add_field(name="Ligne 6:", value=statuses.get("6", "🟢 Opérationnel"), inline=False)
    embed.set_footer(text="Mis à jour par ChronoRails")
    return embed

TRAFFIC_OPTIONS = {
    "operationnel": "🟢 Opérationnel",
    "accident": "🔴 Accident sur la ligne",
    "travaux": "🟠 Fermée pour travaux",
    "traffic": "🟡 Traffic important",
    "fermee_accident": "⚫ Fermée pour accident",
}


@bot.tree.command(name="renvoyer_embed", description="Poster l'embed de statut trafic dans le salon")
@is_staff()
async def renvoyer_embed(interaction: discord.Interaction):
    channel = bot.get_channel(TRAFFIC_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Salon de trafic introuvable.", ephemeral=True)
        return
    
    embed = create_traffic_embed()
    message = await channel.send(embed=embed)
    await interaction.response.send_message("Embed de trafic posté dans le salon.", ephemeral=True)


@bot.tree.command(name="traffic", description="Met à jour le statut trafic d'une ligne")
@is_staff()
@discord.app_commands.describe(
    ligne="Choisissez la ligne à mettre à jour",
    probleme="Choisissez le problème sur la ligne"
)
@discord.app_commands.choices(ligne=[
    discord.app_commands.Choice(name="Ligne 8Bis", value="8Bis"),
    discord.app_commands.Choice(name="Ligne 3Bis", value="3Bis"),
    discord.app_commands.Choice(name="Ligne 6", value="6"),
])
@discord.app_commands.choices(probleme=[
    discord.app_commands.Choice(name="Opérationnel", value="operationnel"),
    discord.app_commands.Choice(name="Accident sur la ligne", value="accident"),
    discord.app_commands.Choice(name="Fermée pour travaux", value="travaux"),
    discord.app_commands.Choice(name="Traffic important", value="traffic"),
    discord.app_commands.Choice(name="Fermée pour accident", value="fermee_accident"),
])
async def traffic(interaction: discord.Interaction, ligne: discord.app_commands.Choice[str], probleme: discord.app_commands.Choice[str]):
    channel = bot.get_channel(TRAFFIC_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Salon de trafic introuvable.", ephemeral=True)
        return

    # Cherche le dernier message du bot dans ce salon
    messages = await channel.history(limit=50).flatten()
    bot_message = None
    for msg in messages:
        if msg.author == bot.user and msg.embeds:
            bot_message = msg
            break

    if bot_message is None:
        await interaction.response.send_message("Aucun message embed du bot trouvé dans ce salon. Utilisez /renvoyer_embed d'abord.", ephemeral=True)
        return

    embed = bot_message.embeds[0]
    # Récupère les champs existants
    fields = {field.name: field.value for field in embed.fields}

    # Met à jour le champ choisi
    new_status = TRAFFIC_OPTIONS.get(probleme.value, "🟢 Opérationnel")
    if ligne.value == "8Bis":
        field_name = "Ligne 8Bis:"
    elif ligne.value == "3Bis":
        field_name = "Ligne 3Bis:"
    else:
        field_name = "Ligne 6:"

    fields[field_name] = new_status

    # Reconstruit l'embed avec les nouveaux statuts
    new_embed = discord.Embed(title=embed.title, color=embed.color)
    for name, val in fields.items():
        new_embed.add_field(name=name, value=val, inline=False)
    new_embed.set_footer(text=embed.footer.text if embed.footer else "")

    await bot_message.edit(embed=new_embed)
    await interaction.response.send_message(f"Statut de {field_name} mis à jour à '{new_status}'.", ephemeral=True)


async def main():
    await run_webserver()
    token = os.getenv("TOKEN")
    if not token:
        print("Erreur : la variable d'environnement TOKEN est manquante !")
        return
    await bot.start(token)

asyncio.run(main())
