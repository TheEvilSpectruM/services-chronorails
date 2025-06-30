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
PRODUCTS_CHANNEL_ID = 1387107501031293120
ROLE_IDS_ALLOWED = [1345857319585714316, 1361714714010189914]

FORM_LINKS = {
    "Staff": "https://docs.google.com/forms/d/1dkl-CJNiUlesD7sSDLJKw0HokJE8zLIrcN4GwD0nGqo/viewform?edit_requested=true",
    "Conducteur [CM]": "https://docs.google.com/forms/d/e/1FAIpQLSe2rxLd7w-rrPtPxxwvOAhDC7YD0J8II-YJn_MEyKhSg0csyQ/viewform?usp=header",
    "PCC": "https://docs.google.com/forms/d/1lCdDmKSKl6uN68oh0IMRnJwtgJE7bZMSSu9kA7xTXYw/viewform?edit_requested=true",
}

PRODUCTS_FILE = "products.json"

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_products(products: dict):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

PRODUCTS = load_products()

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

# Health check Koyeb
async def handle(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def run_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

@bot.tree.command(name="create_product", description="Créer un produit à vendre")
@is_staff()
async def create_product(interaction: discord.Interaction):
    class ProductModal(discord.ui.Modal, title="Nouveau produit"):
        titre = discord.ui.TextInput(label="Titre du modèle", placeholder="Nom du produit")
        description = discord.ui.TextInput(label="Description du modèle", style=discord.TextStyle.paragraph)
        prix = discord.ui.TextInput(label="Prix", placeholder="Par exemple: 10 euros")
        methode = discord.ui.TextInput(label="Méthode d'achat", placeholder="PayPal, Virement, etc.")

        async def on_submit(self, interaction: discord.Interaction):
            title = self.titre.value.strip()
            PRODUCTS[title] = {
                "description": self.description.value,
                "price": self.prix.value,
                "method": self.methode.value,
                "author_id": self.author.id
            }
            save_products(PRODUCTS)

            channel = bot.get_channel(PRODUCTS_CHANNEL_ID)
            embed = discord.Embed(title=title, description=self.description.value, color=0x00ff00)
            embed.add_field(name="Prix", value=self.prix.value, inline=False)
            embed.add_field(name="Méthode d'achat", value=self.methode.value, inline=False)
            embed.set_footer(text=f"Proposé par {self.author.display_name}")
            await channel.send(embed=embed)
            await interaction.response.send_message("Produit ajouté et publié !", ephemeral=True)

    modal = ProductModal()
    modal.author = interaction.user
    await interaction.response.send_modal(modal)

@bot.tree.command(name="buy_product", description="Acheter un produit existant")
@discord.app_commands.describe(titre="Titre du produit que vous souhaitez acheter")
async def buy_product(interaction: discord.Interaction, titre: str):
    produit = PRODUCTS.get(titre)
    if not produit:
        await interaction.response.send_message("❌ Produit introuvable.", ephemeral=True)
        return

    auteur = await bot.fetch_user(produit["author_id"])
    acheteur = interaction.user

    try:
        await auteur.send(f"{acheteur.display_name} souhaite acheter votre produit **{titre}**. Prenez contact avec lui : {acheteur.mention}")
        await interaction.response.send_message("✅ Le créateur du produit a été contacté. Vous serez mis en lien très vite.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Impossible de contacter le créateur du produit. Merci de le mentionner directement.", ephemeral=True)

async def main():
    await run_webserver()
    token = os.getenv("TOKEN")
    if not token:
        print("Erreur : la variable d'environnement TOKEN est manquante !")
        return
    await bot.start(token)

asyncio.run(main())
