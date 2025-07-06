import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput
import os
import json

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
from flask import Flask

import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot en ligne", 200

def run():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run).start()

# --- CONFIGURATION ---

RESULT_CHANNEL_ID = 1359893180014792724
TRAFFIC_CHANNEL_ID = 1379137936796291224
PRODUCTS_CHANNEL_ID = 1387107501031293120  # Salon forum produit

ROLE_IDS_ALLOWED = [1345857319585714316, 1361714714010189914]  # Staff & Responsable réseau

FORM_LINKS = {
    "Staff": "https://docs.google.com/forms/d/1dkl-CJNiUlesD7sSDLJKw0HokJE8zLIrcN4GwD0nGqo/viewform?edit_requested=true",
    "Conducteur [CM]": "https://docs.google.com/forms/d/e/1FAIpQLSe2rxLd7w-rrPtPxxwvOAhDC7YD0J8II-YJn_MEyKhSg0csyQ/viewform?usp=header",
    "PCC": "https://docs.google.com/forms/d/1lCdDmKSKl6uN68oh0IMRnJwtgJE7bZMSSu9kA7xTXYw/viewform?edit_requested=true",
}

PRODUCTS_FILE = "products.json"

TRAFFIC_OPTIONS = {
    "operationnel": "🟢 Opérationnel",
    "accident": "🔴 Accident sur la ligne",
    "travaux": "🟠 Fermée pour travaux",
    "traffic": "🟡 Traffic important",
    "fermee_accident": "⚫ Fermée pour accident",
}

# --- Utilitaires ---

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

# --- Commandes ---

# 1. /statut
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

# 2. /postuler
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

# 3. /resultats
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

    status_text = "passé" if passe.value == "oui" else "pas passé"
    bravo = " 🎉 BRAVO !" if passe.value == "oui" else ""

    message = f"{user.mention}, vous avez {status_text} la formation de **{formation.value}**.{bravo}"

    try:
        await channel.send(message)
    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de l'envoi du message : {e}", ephemeral=True)
        return

    # Ne répondre à l'interaction QUE si elle n’a pas déjà reçu de réponse
    if not interaction.response.is_done():
        await interaction.response.send_message(f"Résultat envoyé dans {channel.mention}", ephemeral=True)


# 4. /renvoyer_embed
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

# 5. /traffic
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

        new_embed = discord.Embed(title=embed.title, color=embed.color, description=embed.description)
        for name, value in fields.items():
            new_embed.add_field(name=name, value=value, inline=False)
        new_embed.set_footer(text=embed.footer.text if embed.footer else "")

        await bot_message.edit(embed=new_embed)
        await interaction.response.send_message(f"Statut de la ligne {ligne.value} mis à jour à : {new_status}", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Erreur lors de la mise à jour : {e}", ephemeral=True)

# 6. /creer_produit (Modal avec champ Tag texte validé)
class ProductModal(Modal):
    def __init__(self, author_id):
        super().__init__(title="Créer un produit")
        self.author_id = author_id

        self.titre = TextInput(label="Titre du modèle à vendre", placeholder="Ex: Modèle Avion X", max_length=100)
        self.description = TextInput(label="Description du modèle", style=discord.TextStyle.paragraph, max_length=500)
        self.prix = TextInput(label="Prix", placeholder="Ex: 10€", max_length=50)
        self.methode = TextInput(label="Méthode d'achat", placeholder="Ex: PayPal, virement...", max_length=100)
        self.tag = TextInput(label="Tag (RATP, SNCF, Station assets, Autre)", max_length=20, placeholder="Ex: SNCF")

        self.add_item(self.titre)
        self.add_item(self.description)
        self.add_item(self.prix)
        self.add_item(self.methode)
        self.add_item(self.tag)

    async def on_submit(self, interaction: discord.Interaction):
        products = load_products()

        titre = self.titre.value.strip()
        description = self.description.value.strip()
        prix = self.prix.value.strip()
        methode = self.methode.value.strip()
        tag_input = self.tag.value.strip()

        valid_tags = ["RATP", "SNCF", "Station assets", "Autre"]
        if tag_input not in valid_tags:
            await interaction.response.send_message(
                f"Tag invalide. Veuillez choisir parmi : {', '.join(valid_tags)}.",
                ephemeral=True
            )
            return

        channel = bot.get_channel(PRODUCTS_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("Salon produit introuvable.", ephemeral=True)
            return
        if not isinstance(channel, discord.ForumChannel):
            await interaction.response.send_message("Le salon produit n'est pas un salon forum valide.", ephemeral=True)
            return

        tag_obj = None
        for t in channel.available_tags:
            if t.name.lower() == tag_input.lower():
                tag_obj = t
                break
        if tag_obj is None:
            await interaction.response.send_message(f"Le tag '{tag_input}' n'existe pas sur ce salon forum.", ephemeral=True)
            return

        products[titre] = {
            "description": description,
            "prix": prix,
            "methode": methode,
            "author_id": self.author_id,
            "tag": tag_input,
        }
        save_products(products)

        try:
            thread = await channel.create_thread(
                name=titre,
                content=f"**Description:** {description}\n**Prix:** {prix}\n**Méthode d'achat:** {methode}",
                auto_archive_duration=1440,
                applied_tags=[tag_obj.id]
            )
            await interaction.response.send_message("Produit créé et posté avec succès !", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Erreur lors de la création du post forum : {e}", ephemeral=True)

@bot.tree.command(name="creer_produit", description="Créer un nouveau produit")
@is_staff()
async def creer_produit(interaction: discord.Interaction):
    modal = ProductModal(author_id=interaction.user.id)
    await interaction.response.send_modal(modal)

# --- EVENT ---

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")

# --- RUN ---

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("Erreur : la variable d'environnement TOKEN est manquante.")
else:
    bot.run(TOKEN)
