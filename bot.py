import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web
import asyncio
import os
import json

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# CONSTANTES
RESULT_CHANNEL_ID = 1359893180014792724  # Salon résultats formations
TRAFFIC_CHANNEL_ID = 1379137936796291224  # (Pour l'embed trafic, si besoin)
PRODUCTS_CHANNEL_ID = 1387107501031293120  # Salon où poster les produits

ROLE_IDS_ALLOWED = [1345857319585714316, 1361714714010189914]  # Staff et Responsable réseau

FORM_LINKS = {
    "Staff": "https://docs.google.com/forms/d/1dkl-CJNiUlesD7sSDLJKw0HokJE8zLIrcN4GwD0nGqo/viewform?edit_requested=true",
    "Conducteur [CM]": "https://docs.google.com/forms/d/e/1FAIpQLSe2rxLd7w-rrPtPxxwvOAhDC7YD0J8II-YJn_MEyKhSg0csyQ/viewform?usp=header",
    "PCC": "https://docs.google.com/forms/d/1lCdDmKSKl6uN68oh0IMRnJwtgJE7bZMSSu9kA7xTXYw/viewform?edit_requested=true",
}

PRODUCTS_FILE = "products.json"

# --- Helpers ---
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
    return app_commands.check(predicate)

def load_products():
    try:
        with open(PRODUCTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_products(products):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=4)


# --- Commandes ---

# 1) /statut
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

# 2) /postuler
@bot.tree.command(
    name="postuler",
    description="Obtenir le lien pour postuler à une formation"
)
@app_commands.describe(formation="Choisissez une formation")
@app_commands.choices(formation=[
    app_commands.Choice(name="Staff", value="Staff"),
    app_commands.Choice(name="Conducteur [CM]", value="Conducteur [CM]"),
    app_commands.Choice(name="PCC", value="PCC"),
])
async def postuler(interaction: discord.Interaction, formation: app_commands.Choice[str]):
    lien = FORM_LINKS.get(formation.value)
    if not lien:
        await interaction.response.send_message("Lien de formulaire introuvable.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"Pour postuler au rôle de **{formation.value}**, cliquez ici : [Cliquez ici]({lien})",
        ephemeral=True
    )

# 3) /resultats
@bot.tree.command(
    name="resultats",
    description="Envoyer les résultats d'une formation à un utilisateur"
)
@is_staff()
@app_commands.describe(
    user="Utilisateur concerné",
    formation="Formation concernée",
    passe="A-t-il passé la formation ?"
)
@app_commands.choices(formation=[
    app_commands.Choice(name="Staff", value="Staff"),
    app_commands.Choice(name="Conducteur [CM]", value="Conducteur [CM]"),
    app_commands.Choice(name="PCC", value="PCC"),
])
@app_commands.choices(passe=[
    app_commands.Choice(name="Oui", value="oui"),
    app_commands.Choice(name="Non", value="non"),
])
async def resultats(interaction: discord.Interaction, user: discord.Member, formation: app_commands.Choice[str], passe: app_commands.Choice[str]):
    channel = bot.get_channel(RESULT_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Le salon de résultats n'a pas été trouvé.", ephemeral=True)
        return

    status_text = "passé" if passe.value == "oui" else "pas passé"
    bravo = " 🎉 BRAVO !" if passe.value == "oui" else ""

    message = f"{user.mention}, vous avez {status_text} la formation de **{formation.value}**.{bravo}"

    await channel.send(message)
    await interaction.response.send_message(f"Résultat envoyé dans {channel.mention}", ephemeral=True)

# 4) /create_product (Modal)
class ProductModal(discord.ui.Modal, title="Créer un produit"):

    titre = discord.ui.TextInput(label="Titre du modèle à vendre", max_length=100)
    description = discord.ui.TextInput(label="Description du modèle", style=discord.TextStyle.paragraph)
    prix = discord.ui.TextInput(label="Prix", max_length=20)
    methode = discord.ui.TextInput(label="Méthode d'achat", max_length=100)

    def __init__(self, author_id: int):
        super().__init__()
        self.author_id = author_id

    async def on_submit(self, interaction: discord.Interaction):
        products = load_products()

        titre = self.titre.value.strip()
        description = self.description.value.strip()
        prix = self.prix.value.strip()
        methode = self.methode.value.strip()

        products[titre] = {
            "description": description,
            "prix": prix,
            "methode": methode,
            "author_id": self.author_id
        }
        save_products(products)

        channel = bot.get_channel(PRODUCTS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title=f"Produit : {titre}", color=0x00ff00)
            embed.add_field(name="Description", value=description, inline=False)
            embed.add_field(name="Prix", value=prix)
            embed.add_field(name="Méthode d'achat", value=methode)
            embed.set_footer(text=f"Créé par {interaction.user.display_name}")

            await channel.send(embed=embed)

        await interaction.response.send_message("Produit créé et posté avec succès !", ephemeral=True)

@bot.tree.command(name="create_product", description="Créer un produit à vendre")
@is_staff()
async def create_product(interaction: discord.Interaction):
    modal = ProductModal(interaction.user.id)
    await interaction.response.send_modal(modal)

# 5) /buy_product
@bot.tree.command(name="buy_product", description="Acheter un produit existant")
@app_commands.describe(titre="Titre du produit à acheter")
async def buy_product(interaction: discord.Interaction, titre: str):
    products = load_products()

    produit = products.get(titre)
    if not produit:
        await interaction.response.send_message(f"Produit '{titre}' introuvable.", ephemeral=True)
        return

    author_id = produit.get("author_id")
    creator = interaction.guild.get_member(author_id)
    if creator is None:
        await interaction.response.send_message("Le créateur du produit n'est pas dans ce serveur.", ephemeral=True)
        return

    try:
        # Envoyer un message privé au créateur
        dm = await creator.create_dm()
        await dm.send(
            f"Bonjour {creator.display_name},\n"
            f"L'utilisateur {interaction.user.mention} souhaite acheter votre produit '{titre}'.\n"
            f"Contactez-le pour finaliser la transaction."
        )
        await interaction.response.send_message(
            f"Vous êtes mis en relation avec le créateur du produit '{titre}'. Il a reçu votre demande en message privé.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "Impossible d'envoyer un message privé au créateur du produit.", ephemeral=True
        )

# --- Serveur web health check (exemple Koyeb) ---
async def handle(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def run_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Commands synced: {len(synced)}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")

async def main():
    await run_webserver()
    token = os.getenv("TOKEN")
    if not token:
        print("Erreur : la variable d'environnement TOKEN est manquante !")
        return
    await bot.start(token)

asyncio.run(main())
