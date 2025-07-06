import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput
import os
import json
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- IDs à configurer ---
RESULT_CHANNEL_ID = 1359893180014792724
TRAFFIC_CHANNEL_ID = 1379137936796291224
PRODUCTS_CHANNEL_ID = 1387107501031293120

ROLE_IDS_ALLOWED = [1345857319585714316, 1361714714010189914]

# --- Formulaires Google ---
FORM_LINKS = {
    "Staff": "https://docs.google.com/forms/d/1dkl-CJNiUlesD7sSDLJKw0HokJE8zLIrcN4GwD0nGqo/viewform?edit_requested=true",
    "Conducteur [CM]": "https://docs.google.com/forms/d/e/1FAIpQLSe2rxLd7w-rrPtPxxwvOAhDC7YD0J8II-YJn_MEyKhSg0csyQ/viewform?usp=header",
    "PCC": "https://docs.google.com/forms/d/1lCdDmKSKl6uN68oh0IMRnJwtgJE7bZMSSu9kA7xTXYw/viewform?edit_requested=true",
}

PRODUCTS_FILE = "products.json"

def load_products():
    try:
        with open(PRODUCTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

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
    return app_commands.check(predicate)

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

@bot.tree.command(name="postuler", description="Obtenir le lien pour postuler à une formation")
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

@bot.tree.command(name="resultats", description="Envoyer les résultats d'une formation à un utilisateur")
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

    status_text = "passé" if passe.value == "oui" else "raté"
    bravo = " 🎉 BRAVO !" if passe.value == "oui" else ""

    message = f"{user.mention}, vous avez {status_text} la formation de **{formation.value}**.{bravo}"

    await channel.send(message)
    await interaction.response.send_message(f"Résultat envoyé dans {channel.mention}", ephemeral=True)

TRAFFIC_OPTIONS = {
    "operationnel": "🟢 Opérationnel",
    "accident": "🔴 Accident sur la ligne",
    "travaux": "🟠 Fermée pour travaux",
    "traffic": "🟡 Traffic important",
    "fermee_accident": "⚫ Fermée pour accident",
}

def create_traffic_embed(statuses=None):
    if statuses is None:
        statuses = {
            "8Bis": "🟢 Opérationnel",
            "3Bis": "🟢 Opérationnel",
            "6": "🟢 Opérationnel"
        }
    embed = discord.Embed(title="INFO TRAFFIC - FTS", color=0x1e90ff)
    embed.add_field(name="Ligne 8Bis:", value=statuses.get("8Bis", "🟢 Opérationnel"), inline=False)
    embed.add_field(name="Ligne 3Bis:", value=statuses.get("3Bis", "🟢 Opérationnel"), inline=False)
    embed.add_field(name="Ligne 6:", value=statuses.get("6", "🟢 Opérationnel"), inline=False)
    embed.set_footer(text="Mis à jour par FTS")
    return embed

@bot.tree.command(name="renvoyer_embed", description="Poster l'embed de statut trafic dans le salon")
@is_staff()
async def renvoyer_embed(interaction: discord.Interaction):
    channel = bot.get_channel(TRAFFIC_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Salon de trafic introuvable.", ephemeral=True)
        return
    
    embed = create_traffic_embed()
    await channel.send(embed=embed)
    await interaction.response.send_message("Embed de trafic posté dans le salon.", ephemeral=True)

@bot.tree.command(name="traffic", description="Met à jour le statut trafic d'une ligne")
@is_staff()
@app_commands.describe(
    ligne="Choisissez la ligne à mettre à jour",
    probleme="Choisissez le problème sur la ligne"
)
@app_commands.choices(ligne=[
    app_commands.Choice(name="Ligne 8Bis", value="8Bis"),
    app_commands.Choice(name="Ligne 3Bis", value="3Bis"),
    app_commands.Choice(name="Ligne 6", value="6"),
])
@app_commands.choices(probleme=[
    app_commands.Choice(name="Opérationnel", value="operationnel"),
    app_commands.Choice(name="Accident sur la ligne", value="accident"),
    app_commands.Choice(name="Fermée pour travaux", value="travaux"),
    app_commands.Choice(name="Traffic important", value="traffic"),
    app_commands.Choice(name="Fermée pour accident", value="fermee_accident"),
])
async def traffic(interaction: discord.Interaction, ligne: app_commands.Choice[str], probleme: app_commands.Choice[str]):
    channel = bot.get_channel(TRAFFIC_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message("Salon de trafic introuvable.", ephemeral=True)
        return

    try:
        bot_message = None
        async for msg in channel.history(limit=50):
            if msg.author == bot.user and msg.embeds:
                bot_message = msg
                break

        if bot_message is None:
            await interaction.response.send_message(
                "Aucun message embed du bot trouvé dans ce salon. Utilisez /renvoyer_embed d'abord.",
                ephemeral=True
            )
            return

        embed = bot_message.embeds[0]
        fields = {field.name: field.value for field in embed.fields}

        new_status = TRAFFIC_OPTIONS.get(probleme.value, "🟢 Opérationnel")

        if ligne.value == "8Bis":
            field_name = "Ligne 8Bis:"
        elif ligne.value == "3Bis":
            field_name = "Ligne 3Bis:"
        else:
            field_name = "Ligne 6:"

        fields[field_name] = new_status

        new_embed = discord.Embed(title=embed.title, color=embed.color)
        for name, val in fields.items():
            new_embed.add_field(name=name, value=val, inline=False)
        new_embed.set_footer(text=embed.footer.text if embed.footer else "")

        await bot_message.edit(embed=new_embed)
        await interaction.response.send_message(f"Statut de {field_name} mis à jour à '{new_status}'.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la mise à jour: {e}", ephemeral=True)

class ProductModal(Modal):
    def __init__(self, author_id):
        super().__init__(title="Créer un produit")
        self.author_id = author_id

        self.titre = TextInput(label="Titre du modèle à vendre", placeholder="Ex: Modèle Avion X", max_length=100)
        self.description = TextInput(label="Description du modèle", style=discord.TextStyle.paragraph, max_length=500)
        self.prix = TextInput(label="Prix", placeholder="Ex: 10€", max_length=50)
        self.methode = TextInput(label="Méthode d'achat", placeholder="Ex: PayPal, virement...", max_length=100)

        self.add_item(self.titre)
        self.add_item(self.description)
        self.add_item(self.prix)
        self.add_item(self.methode)

    async def on_submit(self, interaction: discord.Interaction):
        try:
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
            if channel is None or not isinstance(channel, discord.ForumChannel):
                await interaction.response.send_message("Salon produit introuvable ou invalide.", ephemeral=True)
                return

            await channel.create_thread(
                name=titre,
                content=f"**Description:** {description}\n**Prix:** {prix}\n**Méthode d'achat:** {methode}",
                auto_archive_duration=1440
            )

            await interaction.response.send_message("Produit créé et posté avec succès !", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Une erreur s'est produite : {e}", ephemeral=True)

@bot.tree.command(name="create_product", description="Créer un produit à vendre")
@is_staff()
async def create_product(interaction: discord.Interaction):
    modal = ProductModal(author_id=interaction.user.id)
    await interaction.response.send_modal(modal)

@bot.tree.command(name="buy_product", description="Acheter un produit")
@app_commands.describe(titre="Titre du produit à acheter")
async def buy_product(interaction: discord.Interaction, titre: str):
    products = load_products()
    produit = products.get(titre)
    if not produit:
        await interaction.response.send_message("Produit non trouvé.", ephemeral=True)
        return

    author_id = produit.get("author_id")
    if author_id is None:
        await interaction.response.send_message("Impossible de contacter le vendeur.", ephemeral=True)
        return

    user_acheteur = interaction.user
    user_vendeur = interaction.guild.get_member(author_id)
    if user_vendeur is None:
        await interaction.response.send_message("Le vendeur n'est pas sur ce serveur.", ephemeral=True)
        return

    try:
        dm_channel = await user_vendeur.create_dm()
        await dm_channel.send(
            f"{user_acheteur.mention} souhaite acheter votre produit '{titre}'. Contactez-le pour finaliser la transaction."
        )
        await interaction.response.send_message(
            f"Vous êtes mis en contact avec le vendeur de '{titre}'. Il va vous contacter bientôt.", ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la mise en relation : {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Commands synced: {len(synced)}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation : {e}")

# --- Faux serveur HTTP pour Koyeb ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ChronoRails Bot is running.")

def run_http_server():
    server = HTTPServer(('0.0.0.0', 8000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# --- Lancement du bot ---
async def main():
    token = os.getenv("TOKEN")
    if not token:
        print("Erreur : la variable TOKEN est manquante")
        return
    await bot.start(token)

asyncio.run(main())
