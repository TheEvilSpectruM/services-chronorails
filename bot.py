import os
import discord
from discord.ext import commands

# Configuration des intents
intents = discord.Intents.default()
intents.message_content = True  # Permet de lire le contenu des messages

# Création du bot avec un préfixe "!"
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté !")

# Exemple simple de commande
@bot.command()
async def ping(ctx):
    await ctx.send("Pong !")

# Récupération du token depuis une variable d'environnement pour la sécurité
token = os.getenv("TOKEN")

if token is None:
    print("Erreur : le token du bot n'est pas défini dans la variable d'environnement TOKEN.")
else:
    bot.run(token)
