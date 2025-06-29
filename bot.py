import discord
from discord.ext import commands
import asyncio
from aiohttp import web

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# Mini serveur web pour Koyeb health check
async def handle(request):
    return web.Response(text="OK")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def run_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

async def main():
    await run_webserver()
    await bot.start('mtm4odc2mjgxmtq5njeznjcxna.gpmrko.10ln9abddgtijxxra4ro_obfti5zx16miopbji')

asyncio.run(main())
