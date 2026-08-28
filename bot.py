import os
import io
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Polygon
from PIL import Image as PILImage

# --- Render Keep-Alive Server ---
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
# ---------------------------------

TOKEN = "8912942065:AAEEjoL99zQeqPSmMfRqcJAmBgTuK5PjeXc"

# Conversation States
INV_NUM, INV_DATE, NAME, PHONE, ADDRESS, P_NAME, SIZE, PRICE, QTY, MORE_OR_DONE, DISCOUNT = range(11)

def draw_decorations(canvas, doc):
    canvas.saveState()
    # Top Banner
    top_d = Drawing(595, 45)
    top_d.add(Polygon([0, 45, 595, 45, 595, 10, 0, 35], fillColor=colors.HexColor("#F5A623"), strokeColor=None))
    top_d.add(Polygon([0, 45, 595, 45, 595, 22, 0, 10], fillColor=colors.HexColor("#1A1A1A"), strokeColor=None))
    top_d.drawOn(canvas, 0, 842 - 45)

    # Bottom Banner
    bot_d = Drawing(595, 35)
    bot_d.add(Polygon([0, 20, 595, 35, 595, 20, 0, 10], fillColor=colors.HexColor("#1A1A1A"), strokeColor=None))
    bot_d.add(Polygon([0, 10, 595, 20, 595, 0, 0, 0], fillColor=colors.HexColor("#F5A623"), strokeColor=None))
    bot_d.drawOn(canvas, 0, 0)

    # Footer Text
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(colors.HexColor('#222222'))
    canvas.drawString(36, 42, "Thank you for shopping with Alpha Wear! Visit again.")
    canvas.restoreState()

def get_compressed_logo():
    if os.path.exists("logo.png"):
        try:
            with PILImage.open("logo.png") as img:
                img.thumbnail((300, 300))
                img_io = io.BytesIO()
                img.save(img_io, format='PNG', optimize=True)
                img_io.seek(0)
                rl_img = RLImage(img_io, width=110, height=55)
                rl_img.hAlign = 'LEFT'
                return rl_img
        except Exception as e:
            print(f"Error loading logo: {e}")
            return None
    return None

def create_invoice(inv_num, inv_date, cust_name, cust_phone, cust_address, items, discount):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=55,
        bottomMargin=60
    )
    elements = []
    styles = getSampleStyleSheet()

    brand_address_style = ParagraphStyle('BrandAddress', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#555555'), leading=11)
    invoice_head_style = ParagraphStyle('InvoiceHead', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=30, textColor=colors.HexColor('#222222'), alignment=2)
    meta_label_style = ParagraphStyle('MetaLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#333333'), leading=12)
    meta_val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#4A5568'), leading=12)
    bill_to_label = ParagraphStyle('BillToLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), spaceAfter=2)
    bill_to_text = ParagraphStyle('BillToText', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#4A5568'), leading=12)

    # Header - Clear Logo without duplicate text
    brand_header = []
    logo_img = get_compressed_logo()
    if logo_img:
        brand_header.append(logo_img)
        brand_header.append(Spacer(1, 4))
    
    brand_header.append(Paragraph("1st Floor, ABM Tower, KG School road, Basurhat,<br/>Companiganj, Noakhali, Chittagong, Bangladesh,<br/>3850D", brand_address_style))

    header_table = Table([[brand_header, Paragraph("Invoice", invoice_head_style)]], colWidths=[320, 203])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 0)]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Meta Info
    meta_data = [
        [Paragraph("Date:", meta_label_style), Paragraph(str(inv_date), meta_val_style)],
        [Paragraph("Invoice No.:", meta_label_style), Paragraph(str(inv_num), meta_val_style)],
    ]
    meta_table = Table(meta_data, colWidths=[80, 443])
    meta_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 1)]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # Bill To
    elements.append(Paragraph("Bill To", bill_to_label))
    elements.append(Paragraph(f"<b>{cust_name}</b><br/>Phone: {cust_phone}<br/>{cust_address}", bill_to_text))
    elements.append(Spacer(1, 20))

    # Items Table Header
    table_data = [
        [
            Paragraph("<b>Qty</b>", ParagraphStyle('THC', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
            Paragraph("<b>Description</b>", ParagraphStyle('THL', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=0)),
            Paragraph("<b>Unit Price</b>", ParagraphStyle('THR', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=2)),
            Paragraph("<b>Total</b>", ParagraphStyle('THR2', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=2))
        ]
    ]

    subtotal = 0.0
    for item in items:
        p_name = item['p_name']
        size = item['size']
        price = item['price']
        qty = item['qty']
        tot = qty * price
        subtotal += tot

        desc_str = f"{p_name} ({size})" if size.strip() and size.upper() != 'N/A' else p_name
        
        table_data.append([
            Paragraph(str(qty), ParagraphStyle('TDC', parent=styles['Normal'], alignment=1)),
            Paragraph(desc_str, ParagraphStyle('TDL', parent=styles['Normal'], alignment=0)),
            Paragraph(f"৳{price:.2f}", ParagraphStyle('TDR', parent=styles['Normal'], alignment=2)),
            Paragraph(f"৳{tot:.2f}", ParagraphStyle('TDR2', parent=styles['Normal'], alignment=2))
        ])

    if discount > 0:
        table_data.append([
            Paragraph("1", ParagraphStyle('TDC', parent=styles['Normal'], alignment=1)),
            Paragraph("Discount", ParagraphStyle('TDL', parent=styles['Normal'], alignment=0)),
            Paragraph(f"-৳{discount:.2f}", ParagraphStyle('TDR', parent=styles['Normal'], alignment=2)),
            Paragraph(f"-৳{discount:.2f}", ParagraphStyle('TDR2', parent=styles['Normal'], alignment=2))
        ])

    final_total = max(0.0, subtotal - discount)

    item_table = Table(table_data, colWidths=[55, 268, 100, 100])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3B3B3B')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor('#EEEEEE')),
        ('PADDING', (0,1), (-1,-1), 8),
    ]))
    elements.append(item_table)
    
    # Summary Table Section
    summary_label_style = ParagraphStyle('SumLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), alignment=2)
    summary_val_style = ParagraphStyle('SumVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), alignment=2)

    summary_data = [
        [Paragraph("Subtotal", summary_label_style), Paragraph(f"৳{subtotal:,.2f}", summary_val_style)],
        [Paragraph("Total", summary_label_style), Paragraph(f"৳{final_total:,.2f}", summary_val_style)],
        [Paragraph("Balance", summary_label_style), Paragraph(f"৳{final_total:,.2f}", summary_val_style)],
    ]

    summary_table = Table(summary_data, colWidths=[423, 100])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    
    elements.append(Spacer(1, 20))
    elements.append(summary_table)

    doc.build(elements, onFirstPage=draw_decorations, onLaterPages=draw_decorations)
    buffer.seek(0)
    return buffer

# Form Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📄 Create Invoice", callback_data='start_form')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🛍️ **Alpha Wear - Automatic Invoice Generator**\n\nইনভয়েস তৈরি করতে নিচের বাটনে ক্লিক করুন:"
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

async def start_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['items'] = []
    await query.message.reply_text("🔢 **ইনভয়েস নম্বর (Invoice No.) লিখুন:**")
    return INV_NUM

async def get_inv_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['inv_num'] = update.message.text.strip()
    await update.message.reply_text("📅 **তারিখ (Date) লিখুন (যেমন: 2026-08-28):**")
    return INV_DATE

async def get_inv_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['inv_date'] = update.message.text.strip()
    await update.message.reply_text("👤 **কাস্টমারের নাম লিখুন:**")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("📞 **কাস্টমারের মোবাইল নম্বর দিন:**")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text.strip()
    await update.message.reply_text("📍 **কাস্টমারের পূর্ণাঙ্গ ঠিকানা দিন:**")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text.strip()
    await update.message.reply_text("👕 **প্রোডাক্টের নাম লিখুন:**")
    return P_NAME

async def get_p_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_p_name'] = update.message.text.strip()
    await update.message.reply_text("📏 **প্রোডাক্টের সাইজ লিখুন (যেমন: M, L, XL, XXL) (না থাকলে 'N/A' লিখুন):**")
    return SIZE

async def get_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['current_size'] = update.message.text.strip()
    await update.message.reply_text("💰 **প্রতি পিস প্রোডাক্টের দাম (টাকা):**")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['current_price'] = float(update.message.text.strip())
        await update.message.reply_text("📦 **পরিমাণ (কত পিস):**")
        return QTY
    except ValueError:
        await update.message.reply_text("❌ ভুল হয়েছে! শুধুমাত্র সংখ্যা লিখুন (যেমন: 500 বা 1200):")
        return PRICE

async def get_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text.strip())
        
        item = {
            'p_name': context.user_data['current_p_name'],
            'size': context.user_data['current_size'],
            'price': context.user_data['current_price'],
            'qty': qty
        }
        context.user_data['items'].append(item)

        keyboard = [
            [InlineKeyboardButton("➕ Add Another Product", callback_data='add_more')],
            [InlineKeyboardButton("✅ Done & Discount Options", callback_data='done_items')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        total_items = len(context.user_data['items'])
        await update.message.reply_text(
            f"✅ **প্রোডাক্ট যুক্ত হয়েছে!** (মোট যুক্ত প্রোডাক্ট: {total_items}টি)\n\nআপনি কি আরও প্রোডাক্ট যুক্ত করতে চান, নাকি ডিসকাউন্ট দিতে চান?",
            reply_markup=reply_markup
        )
        return MORE_OR_DONE
    except ValueError:
        await update.message.reply_text("❌ ভুল হয়েছে! শুধুমাত্র সংখ্যা লিখুন (যেমন: 1 বা 2):")
        return QTY

async def handle_more_or_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'add_more':
        await query.message.reply_text("👕 **পরবর্তী প্রোডাক্টের নাম লিখুন:**")
        return P_NAME
    elif query.data == 'done_items':
        await query.message.reply_text("🏷️ **ডিসকাউন্ট প্রাইস (টাকা) (ডিসকাউন্ট না থাকলে '0' লিখুন):**")
        return DISCOUNT

async def get_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        discount = float(update.message.text.strip())
        
        inv_num = context.user_data['inv_num']
        inv_date = context.user_data['inv_date']
        name = context.user_data['name']
        phone = context.user_data['phone']
        address = context.user_data['address']
        items = context.user_data['items']

        await update.message.reply_text("⏳ তথ্য গ্রহণ সম্পন্ন হয়েছে! আপনার Alpha Wear ইনভয়েস তৈরি হচ্ছে...")

        pdf_file = create_invoice(inv_num, inv_date, name, phone, address, items, discount)
        
        subtot = sum(it['qty'] * it['price'] for it in items)
        final_tot = max(0.0, subtot - discount)

        await update.message.reply_document(
            document=pdf_file,
            filename=f"Invoice_{inv_num}_{name}.pdf",
            caption=f"✅ **Alpha Wear - Invoice #{inv_num}**\n👤 Customer: {name}\n📞 Phone: {phone}\n📅 Date: {inv_date}\n📦 Total Items: {len(items)}\n💰 Total: ৳{final_tot:,.2f}"
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ ভুল হয়েছে! ডিসকাউন্ট টাকার অঙ্ক লিখুন (যেমন: 0 বা 100):")
        return DISCOUNT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ইনভয়েস তৈরি বাতিল করা হয়েছে। আবার শুরু করতে /start চাপুন।")
    return ConversationHandler.END

def main():
    keep_alive()
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start_form, pattern='^start_form$')
        ],
        states={
            INV_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_inv_num)],
            INV_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_inv_date)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            P_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_p_name)],
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_size)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_qty)],
            MORE_OR_DONE: [CallbackQueryHandler(handle_more_or_done)],
            DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_discount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    print("Alpha Wear Invoice Bot Active...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
