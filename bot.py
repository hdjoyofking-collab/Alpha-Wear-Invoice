import os
import io
import datetime
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Polygon

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
NAME, PHONE, ADDRESS, P_NAME, SIZE, PRICE, QTY, DISCOUNT = range(8)

# Global Invoice Counter
invoice_counter = 80

def get_top_shape():
    d = Drawing(523, 35)
    d.add(Polygon([0, 35, 523, 35, 523, 5, 0, 25], fillColor=colors.HexColor("#F5A623"), strokeColor=None))
    d.add(Polygon([0, 35, 523, 35, 523, 15, 0, 5], fillColor=colors.HexColor("#1A1A1A"), strokeColor=None))
    return d

def get_bottom_shape():
    d = Drawing(523, 25)
    d.add(Polygon([0, 15, 523, 25, 523, 15, 0, 5], fillColor=colors.HexColor("#1A1A1A"), strokeColor=None))
    d.add(Polygon([0, 5, 523, 15, 523, 0, 0, 0], fillColor=colors.HexColor("#F5A623"), strokeColor=None))
    return d

def create_invoice(cust_name, cust_phone, cust_address, item_name, item_size, price, qty, discount, inv_num):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=20,
        bottomMargin=20
    )
    elements = []

    styles = getSampleStyleSheet()

    brand_title_style = ParagraphStyle('BrandTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, textColor=colors.HexColor('#222222'), spaceAfter=2)
    brand_address_style = ParagraphStyle('BrandAddress', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#555555'), leading=11)
    invoice_head_style = ParagraphStyle('InvoiceHead', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=30, textColor=colors.HexColor('#222222'), alignment=2)
    meta_label_style = ParagraphStyle('MetaLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#333333'), leading=12)
    meta_val_style = ParagraphStyle('MetaVal', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#4A5568'), leading=12)
    bill_to_label = ParagraphStyle('BillToLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), spaceAfter=2)
    bill_to_text = ParagraphStyle('BillToText', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#4A5568'), leading=12)

    elements.append(get_top_shape())
    elements.append(Spacer(1, 10))

    comp_info = [
        Paragraph("<b>ALPHA WEAR</b>", brand_title_style),
        Paragraph("1st Floor, ABM Tower, KG School road, Basurhat,<br/>Companiganj, Noakhali, Chittagong, Bangladesh,<br/>3850D", brand_address_style)
    ]

    header_table = Table([[comp_info, Paragraph("Invoice", invoice_head_style)]], colWidths=[320, 203])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 0)]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    today = datetime.date.today()
    due_date = today + datetime.timedelta(days=30)

    meta_data = [
        [Paragraph("Date:", meta_label_style), Paragraph(today.strftime("%Y-%m-%d"), meta_val_style)],
        [Paragraph("Invoice No.:", meta_label_style), Paragraph(str(inv_num), meta_val_style)],
        [Paragraph("Due Date:", meta_label_style), Paragraph(due_date.strftime("%Y-%m-%d"), meta_val_style)],
    ]

    meta_table = Table(meta_data, colWidths=[80, 443])
    meta_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 1)]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Bill To", bill_to_label))
    elements.append(Paragraph(f"<b>{cust_name}</b><br/>Phone: {cust_phone}<br/>{cust_address}", bill_to_text))
    elements.append(Spacer(1, 15))

    table_data = [
        [
            Paragraph("<b>Qty</b>", ParagraphStyle('THC', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
            Paragraph("<b>Description</b>", ParagraphStyle('THL', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=0)),
            Paragraph("<b>Unit Price</b>", ParagraphStyle('THR', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=2)),
            Paragraph("<b>Total</b>", ParagraphStyle('THR2', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=2))
        ]
    ]

    desc_str = f"{item_name} ({item_size})" if item_size.strip() else item_name
    tot = qty * price
    subtotal = tot

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
    elements.append(Spacer(1, 180))

    summary_label_style = ParagraphStyle('SumLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), alignment=2)
    summary_val_style = ParagraphStyle('SumVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), alignment=2)

    summary_data = [
        [Paragraph("Total", summary_label_style), Paragraph(f"৳{final_total:,.2f}", summary_val_style)],
        [Paragraph("Balance", summary_label_style), Paragraph(f"৳{final_total:,.2f}", summary_val_style)],
    ]

    summary_table = Table(summary_data, colWidths=[423, 100])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Thank you for your business.", ParagraphStyle('FootMsg', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#666666'))))
    elements.append(Spacer(1, 5))
    elements.append(get_bottom_shape())

    doc.build(elements)
    buffer.seek(0)
    return buffer

# Handlers for Form System
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
    await query.message.reply_text("👤 **১/৮: কাস্টমারের নাম লিখুন:**")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("📞 **২/৮: কাস্টমারের মোবাইল নম্বর দিন:**")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text.strip()
    await update.message.reply_text("📍 **৩/৮: কাস্টমারের পূর্ণাঙ্গ ঠিকানা দিন:**")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text.strip()
    await update.message.reply_text("👕 **৪/৮: প্রোডাক্টের নাম লিখুন:**")
    return P_NAME

async def get_p_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['p_name'] = update.message.text.strip()
    await update.message.reply_text("📏 **৫/৮: প্রোডাক্টের সাইজ লিখুন (যেমন: M, L, XL, XXL) (না থাকলে 'N/A' লিখুন):**")
    return SIZE

async def get_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['size'] = update.message.text.strip()
    await update.message.reply_text("💰 **৬/৮: প্রতি পিস প্রোডাক্টের প্রাইস (টাকা):**")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['price'] = float(update.message.text.strip())
        await update.message.reply_text("📦 **৭/৮: মোট কত পিস নিচ্ছেন (পরিমাণ):**")
        return QTY
    except ValueError:
        await update.message.reply_text("❌ ভুল হয়েছে! শুধুমাত্র সংখ্যা লিখুন (যেমন: 500 বা 1200):")
        return PRICE

async def get_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['qty'] = int(update.message.text.strip())
        await update.message.reply_text("🏷️ **৮/৮: ডিসকাউন্ট প্রাইস (টাকা) (ডিসকাউন্ট না থাকলে '0' লিখুন):**")
        return DISCOUNT
    except ValueError:
        await update.message.reply_text("❌ ভুল হয়েছে! শুধুমাত্র পূর্ণসংখ্যার সংখ্যা লিখুন (যেমন: 1 বা 2):")
        return QTY

async def get_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global invoice_counter
    try:
        discount = float(update.message.text.strip())
        context.user_data['discount'] = discount

        await update.message.reply_text("⏳ তথ্য গ্রহণ সম্পন্ন হয়েছে! আপনার Alpha Wear ইনভয়েস তৈরি হচ্ছে...")

        invoice_counter += 1
        inv_num = invoice_counter

        name = context.user_data['name']
        phone = context.user_data['phone']
        address = context.user_data['address']
        p_name = context.user_data['p_name']
        size = context.user_data['size']
        price = context.user_data['price']
        qty = context.user_data['qty']

        pdf_file = create_invoice(name, phone, address, p_name, size, price, qty, discount, inv_num)
        final_tot = max(0.0, (qty * price) - discount)

        await update.message.reply_document(
            document=pdf_file,
            filename=f"Invoice_{inv_num}_{name}.pdf",
            caption=f"✅ **Alpha Wear - Invoice #{inv_num}**\n👤 Customer: {name}\n📞 Phone: {phone}\n💰 Total: ৳{final_tot:,.2f}"
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
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            P_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_p_name)],
            SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_size)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_qty)],
            DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_discount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    print("Alpha Wear Form Invoice Bot Active...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
