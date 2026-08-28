import os
import io
import datetime
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
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

# Global Invoice Counter
invoice_counter = 80

def get_top_shape():
    d = Drawing(523, 40)
    # Background Orange Wave
    d.add(Polygon([0, 40, 523, 40, 523, 10, 0, 30], fillColor=colors.HexColor("#F5A623"), strokeColor=None))
    # Foreground Black Curve
    d.add(Polygon([0, 40, 523, 40, 523, 20, 0, 10], fillColor=colors.HexColor("#1A1A1A"), strokeColor=None))
    return d

def get_bottom_shape():
    d = Drawing(523, 30)
    # Top Black Line
    d.add(Polygon([0, 20, 523, 30, 523, 20, 0, 10], fillColor=colors.HexColor("#1A1A1A"), strokeColor=None))
    # Bottom Orange Banner
    d.add(Polygon([0, 10, 523, 20, 523, 0, 0, 0], fillColor=colors.HexColor("#F5A623"), strokeColor=None))
    return d

def create_invoice(cust_name, cust_address, items_list, inv_num, discount=0):
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

    # Custom Styles
    brand_title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#222222'),
        spaceAfter=3
    )

    brand_address_style = ParagraphStyle(
        'BrandAddress',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor('#555555'),
        leading=11
    )

    invoice_head_style = ParagraphStyle(
        'InvoiceHead',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=28,
        textColor=colors.HexColor('#333333'),
        alignment=2
    )

    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=colors.HexColor('#333333'),
        leading=13
    )

    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        textColor=colors.HexColor('#4A5568'),
        leading=13
    )

    bill_to_label = ParagraphStyle(
        'BillToLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=2
    )

    bill_to_text = ParagraphStyle(
        'BillToText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        textColor=colors.HexColor('#4A5568'),
        leading=13
    )

    # Top Decorative Graphic Banner
    elements.append(get_top_shape())
    elements.append(Spacer(1, 15))

    # Header Row: Company Info (Left) vs "Invoice" Text (Right)
    comp_info = [
        Paragraph("<b>ALPHA WEAR</b>", brand_title_style),
        Paragraph("1st Floor, ABM Tower, KG School road, Basurhat,<br/>Companiganj, Noakhali, Chittagong, Bangladesh,<br/>3850D", brand_address_style)
    ]

    header_table_data = [
        [comp_info, Paragraph("Invoice", invoice_head_style)]
    ]

    header_table = Table(header_table_data, colWidths=[320, 203])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20))

    # Meta Section: Date, Invoice No., Due Date
    today = datetime.date.today()
    due_date = today + datetime.timedelta(days=30)

    meta_data = [
        [Paragraph("Date:", meta_label_style), Paragraph(today.strftime("%Y-%m-%d"), meta_val_style)],
        [Paragraph("Invoice No.:", meta_label_style), Paragraph(str(inv_num), meta_val_style)],
        [Paragraph("Due Date:", meta_label_style), Paragraph(due_date.strftime("%Y-%m-%d"), meta_val_style)],
    ]

    meta_table = Table(meta_data, colWidths=[85, 438])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 1),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 20))

    # Bill To Section
    elements.append(Paragraph("Bill To", bill_to_label))
    elements.append(Paragraph(f"{cust_name}<br/>{cust_address}", bill_to_text))
    elements.append(Spacer(1, 20))

    # Items Table (Qty, Description, Unit Price, Total)
    table_data = [
        [
            Paragraph("<b>Qty</b>", ParagraphStyle('THC', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
            Paragraph("<b>Description</b>", ParagraphStyle('THL', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=0)),
            Paragraph("<b>Unit Price</b>", ParagraphStyle('THR', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=2)),
            Paragraph("<b>Total</b>", ParagraphStyle('THR2', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=2))
        ]
    ]

    subtotal = 0
    for item in items_list:
        p_name, qty, price = item['name'], item['qty'], item['price']
        tot = qty * price
        subtotal += tot
        table_data.append([
            Paragraph(str(qty), ParagraphStyle('TDC', parent=styles['Normal'], alignment=1)),
            Paragraph(p_name, ParagraphStyle('TDL', parent=styles['Normal'], alignment=0)),
            Paragraph(f"৳{price:.2f}", ParagraphStyle('TDR', parent=styles['Normal'], alignment=2)),
            Paragraph(f"৳{tot:.2f}", ParagraphStyle('TDR2', parent=styles['Normal'], alignment=2))
        ])

    if discount > 0:
        subtotal -= discount
        table_data.append([
            Paragraph("1", ParagraphStyle('TDC', parent=styles['Normal'], alignment=1)),
            Paragraph("Discount", ParagraphStyle('TDL', parent=styles['Normal'], alignment=0)),
            Paragraph(f"-৳{discount:.2f}", ParagraphStyle('TDR', parent=styles['Normal'], alignment=2)),
            Paragraph(f"-৳{discount:.2f}", ParagraphStyle('TDR2', parent=styles['Normal'], alignment=2))
        ])

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
    elements.append(Spacer(1, 150)) # Space pushing summary to bottom

    # Summary Section (Total, Balance)
    summary_label_style = ParagraphStyle('SumLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), alignment=2)
    summary_val_style = ParagraphStyle('SumVal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#333333'), alignment=2)

    summary_data = [
        [Paragraph("Total", summary_label_style), Paragraph(f"৳{subtotal:,.2f}", summary_val_style)],
        [Paragraph("Balance", summary_label_style), Paragraph(f"৳{subtotal:,.2f}", summary_val_style)],
    ]

    summary_table = Table(summary_data, colWidths=[423, 100])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Bottom Footer Text & Graphic
    elements.append(Paragraph("Thank you for your business.", ParagraphStyle('FootMsg', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#666666'))))
    elements.append(Spacer(1, 5))
    elements.append(get_bottom_shape())

    doc.build(elements)
    buffer.seek(0)
    return buffer

# Main Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📄 Create Invoice", callback_data='make_memo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🛍️ **Alpha Wear - Automatic Invoice Generator**\n\nইনভয়েস তৈরি করতে নিচের বাটনে ক্লিক করুন:"
    
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
            "📝 **কাস্টমার ও প্রোডাক্টের তথ্য দিন:**\n\n"
            "নিচের ফরম্যাট অনুযায়ী কমা (,) দিয়ে মেসেজ পাঠান:\n\n"
            "`কাস্টমারের নাম, ঠিকানা, প্রোডাক্টের নাম, পরিমাণ, দাম, ডিসকাউন্ট (ঐচ্ছিক)`\n\n"
            "*উদাহরণ (ডিসকাউন্ট ছাড়া):*\n`Ratul, Holishor Chittagong, XL, 1, 599`\n\n"
            "*উদাহরণ (ডিসকাউন্টসহ):*\n`Ratul, Holishor Chittagong, XL, 1, 599, 99`"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global invoice_counter
    step = context.user_data.get('step')
    text = update.message.text.strip()

    if step == 'get_info':
        try:
            parts = [p.strip() for p in text.split(',')]
            name = parts[0]
            address = parts[1]
            p_name = parts[2]
            qty = int(parts[3])
            price = float(parts[4])
            discount = float(parts[5]) if len(parts) > 5 else 0

            items = [{'name': p_name, 'qty': qty, 'price': price}]
            
            invoice_counter += 1
            inv_num = invoice_counter

            await update.message.reply_text("⏳ আপনার Alpha Wear ইনভয়েস তৈরি হচ্ছে...")

            pdf_file = create_invoice(name, address, items, inv_num, discount)
            
            await update.message.reply_document(
                document=pdf_file,
                filename=f"Invoice_{inv_num}_{name}.pdf",
                caption=f"✅ **Alpha Wear - Invoice #{inv_num}**\n👤 Customer: {name}\n💰 Total: ৳{(qty*price)-discount:,.2f}"
            )
            context.user_data['step'] = None

        except Exception:
            await update.message.reply_text("❌ ভুল ফরম্যাট! দয়া করে কমা (,) দিয়ে সঠিকভাবে লিখুন:\n`নাম, ঠিকানা, প্রোডাক্ট, পরিমাণ, দাম, ডিসকাউন্ট`", parse_mode="Markdown")
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
