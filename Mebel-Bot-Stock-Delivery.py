
import json, os, math, datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8989221475:AAHzrlmIpGW1HPxOQ1cD5dcIKzNDXqGqi_Q"
ADMIN_ID = 5791313737

STOCK_FILE = "stock.json"
ZAKAZ_FILE = "zakazlar.txt"

DELIVERY_TEL = "99-901-55-43"
DELIVERY_PRICES = {
    "samovivoz": {"name": "🏭 Ўзи олиб кетиш", "note": "БЕПУЛ"},
    "tashkent": {"name": "🚚 Андижон шаҳар ичи", "note": f"📞 {DELIVERY_TEL}"},
    "tashkent_vil": {"name": "🚚 Андижон вилоят ичи", "note": f"📞 {DELIVERY_TEL}"},
    "viloyat": {"name": "🚛 Вилоятларга", "note": f"📞 {DELIVERY_TEL}"},
}

def load_catalog():
    # try different case variations
    for fname in [STOCK_FILE, "Stock.json", "STOCK.JSON", "stock.JSON"]:
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                return json.load(f)
    # also try lowercase check
    import glob
    for gf in glob.glob("*.json"):
        if "stock" in gf.lower():
            try:
                with open(gf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return data
            except:
                pass
    return {}

def save_catalog(catalog):
    with open(STOCK_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

CATALOG = load_catalog()

CATEGORY_NAMES = {
    "akril": "✨ АКРИЛ",
    "ldsp": "🪵 ЛДСП",
    "lmdf": "🧱 МДФ / ЛМДФ",
    "dsp": "🪚 ДСП",
    "komplekt": "🔧 Кромка / Комплект",
    "boshqa": "📦 Бошқа"
}

user_carts = {}
user_states = {}
PAGE_SIZE = 10

def main_kb():
    kb = []
    for key, products in CATALOG.items():
        if not products: continue
        cname = CATEGORY_NAMES.get(key, key)
        total_qty = sum(p["qty"] for p in products)
        kb.append([InlineKeyboardButton(f"{cname} ({len(products)} тур, {total_qty} дона)", callback_data=f"cat_{key}_0")])
    kb.append([InlineKeyboardButton("🔍 Қидириш", callback_data="search_info"), InlineKeyboardButton("🛒 Саватча", callback_data="cart")])
    return InlineKeyboardMarkup(kb)

def products_kb(cat, page):
    products = CATALOG.get(cat, [])
    total_pages = math.ceil(len(products) / PAGE_SIZE) if products else 1
    start = page * PAGE_SIZE
    kb = []
    for i, p in enumerate(products[start:start+PAGE_SIZE]):
        idx = start + i
        status = "✅" if p["qty"]>5 else "⚠️" if p["qty"]>0 else "❌"
        short = p["name"][:32]
        kb.append([InlineKeyboardButton(f"{status} {short} | {p['qty']}д | {p['price']:,}", callback_data=f"prod_{cat}_{idx}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"cat_{cat}_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages-1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"cat_{cat}_{page+1}"))
    kb.append(nav)
    kb.append([InlineKeyboardButton("⬅️ Бош меню", callback_data="main")])
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_products = sum(len(v) for v in CATALOG.values())
    total_stock = sum(sum(p["qty"] for p in v) for v in CATALOG.values())
    await update.message.reply_text(
        f"Ассалому алайкум! 👋\n\n"
        f"🏭 Омборда: {total_products} тур, {total_stock} дона\n"
        f"📦 ЛДСП, МДФ, АКРИЛ, ДСП\n"
        f"🚚 Доставка: 📞 {DELIVERY_TEL}\n\n"
        f"Категория танланг ёки ном ёзиб қидиринг 👇",
        reply_markup=main_kb()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "main":
        await query.edit_message_text("Категория танланг 👇", reply_markup=main_kb())
    elif data == "noop":
        return
    elif data.startswith("cat_"):
        _, cat, page = data.split("_")
        page = int(page)
        cname = CATEGORY_NAMES.get(cat, cat)
        await query.edit_message_text(f"{cname}:", reply_markup=products_kb(cat, page))
    elif data.startswith("prod_"):
        _, cat, idx = data.split("_")
        idx = int(idx)
        p = CATALOG[cat][idx]
        if p["qty"] <= 0:
            stock_text = "❌ Омборда қолмаган!"
        elif p["qty"] < 5:
            stock_text = f"⚠️ Оз қолди: {p['qty']} дона"
        else:
            stock_text = f"✅ Омборда: {p['qty']} дона бор"
        kb = [
            [InlineKeyboardButton(f"➕ Саватга ({p['qty']} дона бор)", callback_data=f"add_{cat}_{idx}")],
            [InlineKeyboardButton("⬅️ Орқага", callback_data=f"cat_{cat}_{idx//PAGE_SIZE}")]
        ]
        await query.edit_message_text(
            f"📦 <b>{p['name']}</b>\n\n"
            f"💰 Нархи: {p['price']:,} сўм\n"
            f"📊 {stock_text}\n"
            f"🆔 Код: {p['id']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(kb)
        )
    elif data.startswith("add_"):
        _, cat, idx = data.split("_")
        idx = int(idx)
        p = CATALOG[cat][idx]
        if p["qty"] <= 0:
            await query.answer("Омборда қолмаган!", show_alert=True)
            return
        context.user_data["pending_add"] = (cat, idx)
        user_states[user_id] = "waiting_qty"
        await query.edit_message_text(f"{p['name']}\nНеча дона керак? (Омборда {p['qty']} дона бор)\nРақам ёзинг:")

    elif data == "cart":
        cart = user_carts.get(user_id, [])
        if not cart:
            await query.edit_message_text("Сават бўш", reply_markup=main_kb())
            return
        text = "🛒 Сават:\n\n"
        total = 0
        for item in cart:
            p = item["product"]
            qty = item["qty"]
            text += f"• {p['name']} x{qty} = {p['price']*qty:,}\n"
            total += p['price']*qty
        text += f"\nЖами: {total:,} сўм"
        kb = [[InlineKeyboardButton("✅ Буюртма бериш", callback_data="checkout")],[InlineKeyboardButton("🗑 Тозалаш", callback_data="clear"), InlineKeyboardButton("⬅️ Меню", callback_data="main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    elif data == "clear":
        user_carts[user_id] = []
        await query.edit_message_text("Тозаланди", reply_markup=main_kb())

    elif data == "checkout":
        kb = []
        for key, d in DELIVERY_PRICES.items():
            kb.append([InlineKeyboardButton(f"{d['name']} - {d['note']}", callback_data=f"delivery_{key}")])
        await query.edit_message_text("🚚 Доставка турини танланг:", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("delivery_"):
        dkey = data.replace("delivery_", "")
        context.user_data["delivery"] = dkey
        user_states[user_id] = "waiting_name"
        d = DELIVERY_PRICES[dkey]
        await query.edit_message_text(f"Танланди: {d['name']}\n\n👤 Исмингизни ёзинг:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = user_states.get(user_id)

    if state == "waiting_qty":
        try:
            qty_wanted = int(text)
        except:
            await update.message.reply_text("Илтимос фақат рақам ёзинг, масалан: 2")
            return
        cat, idx = context.user_data.get("pending_add")
        p = CATALOG[cat][idx]
        if qty_wanted > p["qty"]:
            await update.message.reply_text(f"❌ Омборда {p['qty']} дона бор холос! Камроқ ёзинг:")
            return
        if qty_wanted <=0:
            await update.message.reply_text("1 дан катта сон ёзинг")
            return
        if user_id not in user_carts:
            user_carts[user_id] = []
        user_carts[user_id].append({"product": p, "qty": qty_wanted, "cat": cat, "idx": idx})
        user_states.pop(user_id, None)
        context.user_data.pop("pending_add", None)
        await update.message.reply_text(f"✅ {p['name']} x{qty_wanted} саватга қўшилди!", reply_markup=main_kb())
        return

    if not state:
        q = text.lower().strip()
        # Категория алиаслари - лотин ва кирилл
        CAT_ALIASES = {
            "ldsp": ["ldsp", "лдсп", "лдcп", "lдсп"],
            "akril": ["akril", "акрил", "акрилл"],
            "lmdf": ["lmdf", "лмдф", "mdf", "мдф", "мдф", "лмдф"],
            "dsp": ["dsp", "дсп", "дcп"],
            "komplekt": ["komplekt", "комплект", "кромка"],
        }
        results = []
        # Агар категория номи ёзилса - шу категорияни тўлиқ қайтар
        for cat_key, aliases in CAT_ALIASES.items():
            if q in aliases or q == cat_key:
                if cat_key in CATALOG:
                    for idx, p in enumerate(CATALOG[cat_key]):
                        results.append((cat_key, idx, p))
                break
        # Агар топилмаса - ном бўйича қидир
        if not results:
            for cat, prods in CATALOG.items():
                for idx, p in enumerate(prods):
                    if q in p["name"].lower():
                        results.append((cat, idx, p))
        if results:
            kb = []
            for cat, idx, p in results[:15]:
                short = p["name"][:32]
                kb.append([InlineKeyboardButton(f"{short} | {p['qty']}д | {p['price']:,}", callback_data=f"prod_{cat}_{idx}")])
            kb.append([InlineKeyboardButton("⬅️ Бош меню", callback_data="main")])
            await update.message.reply_text(f"🔍 '{text}' бўйича {len(results)} та топилди:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text("Топилмади 😕", reply_markup=main_kb())
        return

    if state == "waiting_name":
        context.user_data["name"] = text
        user_states[user_id] = "waiting_phone"
        await update.message.reply_text("📱 Телефон рақамингиз?")
    elif state == "waiting_phone":
        context.user_data["phone"] = text
        user_states[user_id] = "waiting_address"
        await update.message.reply_text("📍 Тўлиқ манзил (доставка учун):")
    elif state == "waiting_address":
        context.user_data["address"] = text
        delivery_key = context.user_data.get("delivery", "samovivoz")
        delivery = DELIVERY_PRICES[delivery_key]
        name = context.user_data.get("name")
        phone = context.user_data.get("phone")
        address = context.user_data.get("address")
        cart = user_carts.get(user_id, [])

        total_mat = sum(item["product"]["price"]*item["qty"] for item in cart)

        for item in cart:
            cat = item["cat"]
            idx = item["idx"]
            qty = item["qty"]
            CATALOG[cat][idx]["qty"] -= qty
            if CATALOG[cat][idx]["qty"] <0:
                CATALOG[cat][idx]["qty"] = 0
        save_catalog(CATALOG)

        cart_text = "\n".join([f"- {i['product']['name']} x{i['qty']} = {i['product']['price']*i['qty']:,}" for i in cart]) or "Ёзма буюртма"

        admin_msg = (
            f"🔥 ЯНГИ ЗАКАЗ\n\n"
            f"👤 {name}\n📱 {phone}\n📍 {address}\n\n"
            f"📦 Материаллар:\n{cart_text}\n\n"
            f"🚚 Доставка: {delivery['name']} - {delivery['note']}\n"
            f"💰 Жами: {total_mat:,} сўм\n"
            f"🕒 {datetime.datetime.now().strftime('%d.%m %H:%M')}\nID: {user_id}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        except Exception as e:
            print(e)

        with open(ZAKAZ_FILE, "a", encoding="utf-8") as f:
            f.write(admin_msg + "\n---\n")

        client_msg = (
            f"✅ Заказингиз қабул қилинди!\n\n"
            f"📦 {cart_text}\n"
            f"🚚 Доставка: {delivery['name']} - 📞 {DELIVERY_TEL}\n"
            f"💰 Жами: {total_mat:,} сўм\n\n"
            f"Тез орада боғланамиз. Раҳмат! 🙏"
        )

        user_carts[user_id] = []
        user_states.pop(user_id, None)
        context.user_data.clear()
        await update.message.reply_text(client_msg, reply_markup=main_kb())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
