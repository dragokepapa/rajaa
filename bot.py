from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import Config
from game import Game
from database import db
import logging

logging.basicConfig(level=logging.INFO)

app = Client("RajaMantri_Pro", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)

games = {}   # chat_id: Game

STORE_ITEMS = {
    "crown": {"name": "👑 Raja Crown", "price": 250, "emoji": "👑"},
    "shield": {"name": "🛡️ Sipahi Shield", "price": 180, "emoji": "🛡️"},
    "mask": {"name": "😈 Chor Mask", "price": 150, "emoji": "😈"},
}

# ====================== START ======================
@app.on_message(filters.command("start") & filters.private)
async def start(_, msg: Message):
    await msg.reply(f"""
👑 **Raja Mantri Pro Bot**

Group mein add karke /startgame karo!
/profile | /store | /daily | /leaderboard

Made with ❤️
    """)

# ====================== GAME COMMANDS ======================
@app.on_message(filters.command("startgame") & filters.group)
async def startgame(_, msg: Message):
    chat_id = msg.chat.id
    if chat_id in games:
        return await msg.reply("⚠️ Ek game already chal rahi hai!")
    games[chat_id] = Game()
    await msg.reply("🎮 **Game Started!**\n\n/join karo (4 players needed)")

@app.on_message(filters.command("join") & filters.group)
async def join(_, msg: Message):
    chat_id = msg.chat.id
    if chat_id not in games:
        return await msg.reply("Pehle /startgame karo!")
    game = games[chat_id]
    user = msg.from_user
    if user.id in game.players:
        return await msg.reply("Already joined!")
    if game.is_full():
        return await msg.reply("Game full ho gayi!")
    game.add_player(user.id, user.first_name)
    await msg.reply(f"✅ {user.mention} joined! ({len(game.players)}/4)")
    if game.is_full():
        await start_round(msg, game)

async def start_round(msg, game):
    game.assign_roles()
    for uid, role in game.roles.items():
        try:
            await app.send_message(uid, game.get_role_text(uid))
        except:
            pass
    raja = next(uid for uid, r in game.roles.items() if r == "Raja")
    await msg.reply(f"👑 **Raja Revealed**: [Player](tg://user?id={raja})")

    buttons = []
    row = []
    for uid in game.players:
        if uid != game.mantri:
            user = await app.get_users(uid)
            row.append(InlineKeyboardButton(user.first_name, callback_data=f"guess_{uid}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)
    await msg.reply("🕵️ **Mantri ji, Chor kaun hai?**", reply_markup=InlineKeyboardMarkup(buttons))

# ====================== GUESS HANDLER ======================
@app.on_callback_query(filters.regex("^guess_"))
async def handle_guess(client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    game = games.get(chat_id)
    if not game or callback.from_user.id != game.mantri:
        return await callback.answer("Sirf Mantri guess kar sakta hai!", show_alert=True)

    guessed_id = int(callback.data.split("_")[1])
    is_correct = game.check_guess(guessed_id)
    result = "✅ **Mantri Jeet Gaya!**" if is_correct else "🚨 **Chor Jeet Gaya!**"

    game.update_points(is_correct)

    reveal = f"{result}\n\n**Round {game.current_round} Results:**\n"
    for uid, role in game.roles.items():
        u = await client.get_users(uid)
        pts = 30 if ((is_correct and role == "Mantri") or (not is_correct and role == "Chor")) else 10
        reveal += f"• {u.first_name} → **{role}** (+{pts} pts)\n"

    await callback.message.edit_text(reveal)

    if game.current_round < game.max_rounds:
        game.current_round += 1
        await callback.message.reply(f"🎲 **Round {game.current_round}/{game.max_rounds}** shuru!")
        await start_round(callback.message, game)
    else:
        # Final Rewards
        game.give_end_game_rewards()
        ranking = game.get_final_ranking()
        final_text = "🏆 **Game Over - Final Ranking**\n\n"
        positions = ["🥇 1st", "🥈 2nd", "🥉 3rd", "💀 4th"]
        rewards = [100, 50, 0, -50]
        for i, (uid, pts) in enumerate(ranking):
            user = await client.get_users(uid)
            coin = rewards[i]
            sign = "+" if coin >= 0 else ""
            final_text += f"{positions[i]} → **{user.first_name}** ({pts} pts) → **{sign}{coin} coins**\n"
        await callback.message.reply(final_text)
        del games[chat_id]

# ====================== PROFILE ======================
@app.on_message(filters.command("profile"))
async def profile(_, msg: Message):
    user = msg.from_user
    data = db.get_user_data(user.id)
    if not data:
        return await msg.reply("Abhi tak koi game nahi kheli! Khelo pehle.")

    _, wins, played, coins, inv = data
    winrate = round((wins / played) * 100, 1) if played else 0
    badges = " ".join(db.get_inventory(user.id)) or "Koi badge nahi"

    card = f"""
╔══════════════════════════════╗
       👑 RAJA MANTRI PRO       
         **TRAINER CARD**        
╠══════════════════════════════╣
**Player :** {user.first_name}
**ID     :** `{user.id}`
**Coins  :** 💰 {coins}
**Wins   :** {wins} | **Games:** {played}
**WinRate:** {winrate}%
**Badges :** {badges}
╚══════════════════════════════╝
    """
    await msg.reply(card)

# ====================== STORE ======================
@app.on_message(filters.command("store"))
async def store(_, msg: Message):
    buttons = [[InlineKeyboardButton(f"{item['emoji']} {item['name']} - {item['price']} coins", callback_data=f"buy_{iid}")] for iid, item in STORE_ITEMS.items()]
    await msg.reply("🛒 **Raja Mantri Store**", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex("^buy_"))
async def handle_buy(_, callback: CallbackQuery):
    item_id = callback.data.split("_")[1]
    item = STORE_ITEMS.get(item_id)
    if not item: return
    if db.get_coins(callback.from_user.id) < item["price"]:
        return await callback.answer("❌ Enough coins nahi hain!", show_alert=True)
    db.add_coins(callback.from_user.id, -item["price"])
    db.add_to_inventory(callback.from_user.id, item["emoji"])
    await callback.answer(f"✅ {item['name']} kharid liya!", show_alert=True)

# ====================== OTHER COMMANDS ======================
@app.on_message(filters.command("daily"))
async def daily(_, msg: Message):
    if db.claim_daily(msg.from_user.id):
        await msg.reply("🎁 **Daily Reward!** +50 coins mil gaye!")
    else:
        await msg.reply("⏳ Aaj already le chuke ho. Kal aana!")

@app.on_message(filters.command("leaderboard"))
async def leaderboard(_, msg: Message):
    data = db.get_leaderboard()
    text = "🏆 **Global Leaderboard**\n\n"
    for i, (u, w, p) in enumerate(data, 1):
        text += f"{i}. **{u}** — {w} wins ({p} games)\n"
    await msg.reply(text or "Abhi koi data nahi hai.")

@app.on_message(filters.command(["addsudo", "removesudo", "addcoins"]) & filters.user(Config.OWNER_ID))
async def sudo_cmds(_, msg: Message):
    cmd = msg.command[0]
    try:
        user_id = int(msg.command[1])
        if cmd == "addsudo":
            db.add_sudo(user_id)
            await msg.reply(f"✅ {user_id} sudo bana diya!")
        elif cmd == "removesudo":
            db.remove_sudo(user_id)
            await msg.reply(f"✅ {user_id} sudo se hataya!")
        else:
            amount = int(msg.command[2])
            db.add_coins(user_id, amount)
            await msg.reply(f"✅ {amount} coins diye {user_id} ko!")
    except:
        await msg.reply(f"Usage: /{cmd} <user_id> [amount]")

@app.on_message(filters.command("endgame") & filters.group)
async def endgame(_, msg: Message):
    chat_id = msg.chat.id
    if chat_id in games:
        del games[chat_id]
        await msg.reply("🛑 Game end kar di!")
    else:
        await msg.reply("Koi game nahi chal rahi.")

app.run()