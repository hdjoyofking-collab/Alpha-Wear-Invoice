import os
import io
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- Render 24/7 Keep-Alive Server ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Alpha Wear Invoice Bot is active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
# -------------------------------------

# Updated Token
TOKEN = "8912942065:AAEEjoL99zQeqPSmMfRqcJAmBgTuK5PjeXc"

# PDF Invoice Generator Function
def create_invoice(cust_name, cust_phone, cust_address, items_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=26,
        textColor=colors.HexColor('#D4AF37'), # Gold Color matching logo
        alignment=0,
        spaceAfter=2
    )
    
    tagline_style = ParagraphStyle(
        'TaglineStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#1A1A1A'),
        spaceAfter=6
    )

    address_style = ParagraphStyle(
        'AddressStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=15
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=3
    )

    # Business Header - Alpha Wear Details
    elements.append(Paragraph("ALPHA WEAR", title_style))
    elements.append(Paragraph("PREMIUM APPAREL & STYLE", tagline_style))
    elements.append(Paragraph("<b>Showroom:</b> 1st Floor, ABM Tower, KG School road, Basurhat, Companiganj, Noakhali.<br/><b>Phone:</b> 01805503485, 01609761385 | <b>Email:</b> alphawearbd@gmail.com", address_style))
    elements.append(Spacer(1, 10))

    # Customer Details Box
    cust_info = [
        [Paragraph(f"<b>Customer Name:</b> {cust_name}", normal_style), Paragraph(f"<b>Invoice Type:</b> Cash Memo", normal_style)],
        [Paragraph(f"<b>Phone:</b> {cust_phone}", normal_style), Paragraph(f"<b>Payment:</b> Cash on Delivery", normal_style)],
        [Paragraph(f"<b>Address:</b> {cust_address}", normal_style), Paragraph("", normal_style)]
    ]
    
    cust_table = Table(cust_info, colWidths=[280, 240])
    cust_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E0')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(cust_table)
    elements.append(Spacer(1, 20))

    # Items Table Data
    table_data = [["Item Description", "Qty", "Price (BDT)", "Total (BDT)"]]
    grand_total = 0

    for item in items_list:
        p_name, qty, price = item['name'], item['qty'], item['price']
        total = qty * price
        grand_total += total
        table_data.append([p_name, str(qty), f"{price:.2f}", f"{total:.2f}"])

    table_data.append(["", "", "Grand Total:", f"{grand_total:.2f} BDT"])

    item_table = Table(table_data, colWidths=[250, 60, 105, 105])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A1A1A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#D4AF37')), # Gold Text
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#E2E8F0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (2,-1), (-1,-1), colors.HexColor('#EDF2F7')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    
    elements.append(item_table)
    elements.append(Spacer(1, 30))
    
    # Footer
    elements.append(Paragraph("<b>Thank you for shopping with Alpha Wear!</b><br/>FB/IG/TikTok: @alphawear.bd", ParagraphStyle('Footer', alignment=1, fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#1A1A1A'))))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Main Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📄 Create Cash Memo", callback_data='make_memo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🛍️ **Alpha Wear - Automatic Invoice Generator**\n\nক্যাশ মেমো তৈরি করতে নিচের বাটনে ক্লিক করুন:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'make_memo':
        context.user_data['step'] = 'get_info'
        msg = (
            "📝 **কাস্টমার ও প্রোডাক্ট তথ্য পাঠান:**\n\n"
            "নিচের ফরম্যাট অনুযায়ী কমা (,) ব্যবহার করে মেসেজ দিন:\n\n"
            "`কাস্টমারের নাম, ফোন নম্বর, ঠিকানা, প্রোডাক্টের নাম, পরিমাণ, দাম`\n\n"
            "*উদাহরণ:* \n`Mahim, 01800000000, Basurhat, Premium T-Shirt, 2, 500`"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step')
    text = update.message.text.strip()

    if step == 'get_info':
        try:
            parts = [p.strip() for p in text.split(',')]
            name = parts[0]
            phone = parts[1]
            address = parts[2]
            p_name = parts[3]
            qty = int(parts[4])
            price = float(parts[5])

            items = [{'name': p_name, 'qty': qty, 'price': price}]

            await update.message.reply_text("⏳ আপনার Alpha Wear ক্যাশ মেমো তৈরি হচ্ছে...")

            pdf_file = create_invoice(name, phone, address, items)
            
            await update.message.reply_document(
                document=pdf_file,
                filename=f"AlphaWear_Invoice_{name}.pdf",
                caption=f"✅ **Alpha Wear - Cash Memo**\n👤 Customer: {name}\n💰 Total: ৳{qty*price:.2f}"
            )
            context.user_data['step'] = None

        except Exception:
            await update.message.reply_text("❌ ভুল ফরম্যাট! দয়া করে কমা (,) দিয়ে সঠিকভাবে লিখুন:\n`নাম, মোবাইল, ঠিকানা, প্রোডাক্ট, পরিমাণ, দাম`", parse_mode="Markdown")
    else:
        await start(update, context)

def main():
    keep_alive()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Alpha Wear Invoice Bot Active...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
