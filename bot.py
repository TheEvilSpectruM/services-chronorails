import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os
import json

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

RESULT_CHANNEL_ID = 1359893180014792724
TRAFFIC_CHANNEL_ID = 1379137936796291224
MARKET_CHANNEL_ID = 1387107501031293120

ROLE_IDS_ALLOWED = [1345857319585714316, 1361714714010189914]

FORM_LINKS = {
    "Staff": "https://docs.google.com/forms/d/1dkl-CJNiUlesD7sSDLJKw0HokJE8zLIrcN4GwD0nGqo/viewform?edit_requested=true",
    "Conducteur [CM]": "https://docs.google.com/forms/d/e/1FAIpQLSe2rxLd7w-rrPtPxxwvOAhDC7YD0J8II-YJn_MEyKhSg0csyQ/viewform?usp=header",
    "PCC": "https://docs.google.com/forms/d/1lCdDmKSKl6uN68oh0IMRnJwtgJE7bZMSSu9kA7xTXYw/viewform?edit_requested=true",
}

PRODUCTS_FILE = "products.json"

def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

def save_products(products):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(products, f, indent=4)

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

# Health check pour hébergement
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
    emoji, texte = {
        discord.Status.online: ("🟢", "En ligne"),
        discord.Status.idle: ("🟡", "Problèmes mineurs"),
        discord.Status.offline: ("🔴", "Hors Ligne"),
        discord.Status.invisible: ("🔴", "Hors Ligne")
    }.get(status, ("❔", "Statut inconnu"))
    await interaction.response.send_message(f"Statut du bot : {emoji} {texte}")

@bot.tree.command(name="postuler", description="Obtenir le lien pour postuler à une formation")
@discord.app_commands.choices(formation=[
    discord.app_commands.Choice(name="Staff", value="Staff"),
    discord.app_commands.Choice(name="Conducteur [CM]", value="Conducteur [CM]"),
    discord.app_commands.Choice(name="PCC", value="PCC")
])
async def postuler(interaction: discord.Interaction, formation: discord.app_commands.Choice[str]):
    lien = FORM_LINKS.get(formation.value)
    if not lien:
        await interaction.response.send_message("Lien de formulaire introuvable.", ephemeral=True)
        return
    await interaction.response.send_message(f"Pour postuler au rôle de **{formation.value}**, cliquez ici : [Cliquez ici]({lien})", ephemeral=True)

@bot.tree.command(name="resultats", description="Envoyer les résultats d'une formation à un utilisateur")
@is_staff()
@discord.app_commands.choices(formation=[
    discord.app_commands.Choice(name="Staff", value="Staff"),
    discord.app_commands.Choice(name="Conducteur [CM]", value="Conducteur [CM]"),
    discord.app_commands.Choice(name="PCC", value="PCC")
])
@discord.app_commands.choices(passe=[
    discord.app_commands.Choice(name="Oui", value="oui"),
    discord.app_commands.Choice(name="Non", value="non")
])
async def resultats(interaction: discord.Interaction, user: discord.Member, formation: discord.app_commands.Choice[str], passe: discord.app_commands.Choice[str]):
    channel = bot.get_channel(RESULT_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Le salon de résultats n'a pas été trouvé.", ephemeral=True)
        return
    message = f"{user.mention}, vous avez {'passé' if passe.value == 'oui' else 'pas passé'} la formation de **{formation.value}**.{" 🎉 BRAVO !" if passe.value == 'oui' else ''}"
    await channel.send(message)
    await interaction.response.send_message(f"Résultat envoyé dans {channel.mention}", ephemeral=True)

@bot.tree.command(name="create_product", description="Créer un produit à vendre")
@is_staff()
async def create_product(interaction: discord.Interaction):
    await interaction.response.send_modal(ProductModal(author_id=interaction.user.id))

class ProductModal(discord.ui.Modal, title="Créer un produit"):
    titre = discord.ui.TextInput(label="Titre du modèle", max_length=100)
    description = discord.ui.TextInput(label="Description du modèle", style=discord.TextStyle.paragraph)
    prix = discord.ui.TextInput(label="Prix")
    methode = discord.ui.TextInput(label="Méthode d'achat")

    def __init__(self, author_id):
        super().__init__()
        self.author_id = author_id

    async def on_submit(self, interaction: discord.Interaction):
        products = load_products()
        product = {
            "titre": self.titre.value,
            "description": self.description.value,
            "prix": self.prix.value,
            "methode": self.methode.value,
            "author_id": self.author_id
        }
        products.append(product)
        save_products(products)

        channel = bot.get_channel(MARKET_CHANNEL_ID)
        embed = discord.Embed(title=self.titre.value, description=self.description.value, color=0x00ff00)
        embed.add_field(name="Prix", value=self.prix.value)
        embed.add_field(name="Méthode d'achat", value=self.methode.value)
        embed.set_footer(text=f"Ajouté par {interaction.user.display_name}")
        await channel.send(embed=embed)
        await interaction.response.send_message("Produit créé avec succès.", ephemeral=True)

@bot.tree.command(name="buy_product", description="Acheter un produit par son titre")
@discord.app_commands.describe(titre="Titre du produit à acheter")
async def buy_product(interaction: discord.Interaction, titre: str):
    products = load_products()
    match = next((p for p in products if p['titre'].lower() == titre.lower()), None)
    if not match:
        await interaction.response.send_message("Produit introuvable.", ephemeral=True)
        return
    seller = await bot.fetch_user(match['author_id'])
    await seller.send(f"{interaction.user.name} souhaite acheter votre produit : **{match['titre']}**")
    await interaction.response.send_message("Le vendeur a été notifié en message privé.", ephemeral=True)

async def main():
    await run_webserver()
    token = os.getenv("TOKEN")
    if not token:
        print("Erreur : TOKEN non défini !")
        return
    await bot.start(token)

asyncio.run(main())
