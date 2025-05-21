import re
from flask import Flask, render_template, request, redirect, flash, url_for
import pandas as pd
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import csv
from datetime import datetime
from flask import jsonify
from flask import send_file




app = Flask(__name__)
app.secret_key = 'your_super_secret_key'  # Use a strong secret key

# Email configuration
SENDER_EMAIL = 'your_mail_id'    
SENDER_PASSWORD = 'password'    #use app password
SMTP_SERVER = 'smtp.office365.com'
SMTP_PORT = 587

def clean_company_profile(path):
    """Clean and standardize Company Profile data"""
    df = pd.read_excel(path)
    df.rename(columns={
        'Patner': 'Partner',
        'CAS No.': 'CAS#'
    }, inplace=True)
    df = df.fillna('N/A') 
    return df

def clean_chemical_weekly(path):
    """Clean and standardize Chemical Weekly data"""
    df = pd.read_excel(path)
    df.rename(columns={
        'Cas No.': 'CAS#'
    }, inplace=True)
    df = df.fillna('N/A')
    return df

def clean_network_partner(path):
    """Clean and standardize Network Partner data"""
    raw_df = pd.read_excel(path, header=None)
    
    # Find first valid header row
    for i in range(len(raw_df)):
        row = raw_df.iloc[i]
        if 'Product Name' in row.values:
            raw_df.columns = raw_df.iloc[i]
            df = raw_df[i+1:].copy()
            break
    else:
        return pd.DataFrame()  # fallback empty

    df.rename(columns={
        'CAS No.': 'CAS#',
    }, inplace=True)
    df = df.fillna('N/A')
    return df

# Load and process all data files
data_dir = "data"
files = {
    "Company Profile": clean_company_profile(os.path.join(data_dir, "Company profile.xlsx")),
    "Network Partner": clean_network_partner(os.path.join(data_dir, "NP.xlsx")),
    "Chemical Weekly": clean_chemical_weekly(os.path.join(data_dir, "chemical Weekly.xlsx")),
}

# Standardize column names across all dataframes
for df in files.values():
    df.columns = df.columns.str.strip()

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main search route"""
    results = []

    if request.method == 'POST':
        query = request.form['query'].strip().lower()

        for source, df in files.items():
            for _, row in df.iterrows():
                product_name = str(row.get('Product Name', '')).lower()
                cas = str(row.get('CAS#', '')).lower()
                partner = str(row.get('Partner', '')).lower()

                if query in product_name or query in cas or query in partner:
                    results.append({
                        'source': source,
                        'Partner': row.get('Partner', ''),
                        'Product Name': row.get('Product Name', ''),
                        'CAS#': row.get('CAS#', ''),
                        'Category': row.get('Category', ''),
                        'Details': row.get('Details', ''),
                        'Remarks': row.get('Remarks', ''),
                        'Email id': row.get('Email id', '')
                    })

        # Sort after collecting results
        results.sort(key=lambda x: x.get('Partner', '').lower())

    return render_template('index.html', results=results)
    




@app.route('/send_email', methods=['POST'])
@app.route('/send_email', methods=['POST'])
def send_email():
    """Handle email sending for product inquiries"""
    product = request.form.get('product_name', '').strip()
    cas = request.form.get('cas', '').strip()
    quantities = request.form.getlist('quantity[]')
    units = request.form.getlist('unit[]')

    quantity_info = ', '.join(f"{q} {u}" for q, u in zip(quantities, units))
    remarks = request.form.get('remarks', '').strip()
    remarks_row = ""
    if remarks:
        remarks_row = f"""
        <tr><td style="padding: 8px;"><strong>Remarks</strong></td><td style="padding: 8px;">{remarks}</td></tr>
        """

    # Get emails from the form
    partner_email = request.form.get('email', '').strip()
    manual_email_list = request.form.get('email_list', '').strip()

    # Combine emails
    email_list = []
    if partner_email and '@' in partner_email:
        email_list.append(partner_email)
    if manual_email_list:
        manual_emails = [email.strip() for email in manual_email_list.split(',') if '@' in email]
        email_list.extend(manual_emails)

    if not email_list:
        flash("No valid email addresses provided", "error")
        return redirect('/')

    primary_recipient = email_list[0]
    cc_recipients = ['default_mail', 'default_mail'] + email_list[1:]  # add your default mail ids

    # Email subject
    subject = f"Inquiry for {product} (CAS: {cas})"

    # Construct HTML content
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <p>Dear Sir/Madam,</p>
            <p><strong>Greetings from Covenants PharmaChem!</strong></p>
            <p>Covenants PharmaChem provides Sourcing, Contract Manufacturing, Customs Research, Impurity Synthesis, Small Molecule development services through its 110+ network partners all over India. We have capabilities from Gram to Metric Ton scale for all the complex chemical reactions.</p>
            <p>For one of our project, we are looking for:</p>

            
            
            <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0;">
                <tr><td style="padding: 8px;"><strong>Product Name</strong></td><td style="padding: 8px;">{product}</td></tr>
                <tr><td style="padding: 8px;"><strong>CAS Number</strong></td><td style="padding: 8px;">{cas}</td></tr>
                <tr><td style="padding: 8px;"><strong>Quantity</strong></td><td style="padding: 8px;">{quantity_info}</td></tr>
                {remarks_row}
            </table>

            <p>Request to give your best offer along with lead time, COA/Specs, Packing size & HSN codes.</p>

            <p>Best regards,<br>Sachin<br>Sourcing Team</p>
            <p><strong>Covenants PharmaChem LLP</strong><br>
            Email: info@covenantspc.com<br>
            Website: www.covenantspc.com<br>
            Contact no: +91 8452008095 / 93
            </p>

            <!-- Logo Image at Bottom -->
            <div style="margin-top: 20px; text-align: left;">
                <img src="cid:logo_cid" alt="Company Logo" style="max-width: 200px; height: auto;">
            </div>
        </body>
    </html>
    """

    try:
        # Create the email
        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = primary_recipient
        msg['Cc'] = ', '.join(cc_recipients)

        # HTML part
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)
        msg_alternative.attach(MIMEText(html, 'html'))

        # Attach logo from static folder
        with open('static/logo_bottom.png', 'rb') as img_file:
            logo = MIMEImage(img_file.read())
            logo.add_header('Content-ID', '<logo_cid>')  # Very important
            logo.add_header('Content-Disposition', 'inline', filename="logo_bottom.png")
            msg.attach(logo)

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            all_recipients = [primary_recipient] + cc_recipients
            server.sendmail(SENDER_EMAIL, all_recipients, msg.as_string())

        # Log inquiry
        log_file = 'logs/inquiries.csv'
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['timestamp', 'product_name', 'cas', 'quantities', 'units', 'partner', 'emails'])
            writer.writerow([
                datetime.now().isoformat(),
                product,
                cas,
                ', '.join(quantities),
                ', '.join(units),
                request.form.get('partner', ''),
                ', '.join(email_list)
            ])

        flash(f"Inquiry sent for {quantity_info} of {product} to {', '.join(email_list)}", "success")
    
    except Exception as e:
        flash(f"Failed to send email: {str(e)}", "error")
        app.logger.error(f"Email error: {str(e)}")

    return redirect('/')

@app.route('/send_bulk_email', methods=['POST'])
@app.route('/send_bulk_email', methods=['POST'])
def send_bulk_email():
    """Handle sending bulk inquiries"""
    data_list = request.get_json()
    if not data_list:
        return jsonify({'message': 'No data received.'}), 400

    success_count = 0
    failure_count = 0

    for data in data_list:
        try:
            product = data.get('product_name', '').strip()
            cas = data.get('cas', '').strip()
            quantities = data.get('quantity[]', [])
            units = data.get('unit[]', [])
            remarks = data.get('remarks', '').strip()

            remarks_row = ""
            if remarks:
                remarks_row = f"""
                <tr><td style="padding: 8px;"><strong>Remarks</strong></td><td style="padding: 8px;">{remarks}</td></tr>
                """

            partner_email = data.get('email', '').strip()
            manual_email_list = data.get('email_list', '').strip()

            email_list = []
            if partner_email and '@' in partner_email:
                email_list.append(partner_email)
            if manual_email_list:
                manual_emails = [email.strip() for email in manual_email_list.split(',') if '@' in email]
                email_list.extend(manual_emails)

            if not email_list:
                continue

            primary_recipient = email_list[0]
            cc_recipients = ['alpesh@covenantspc.com', 'vivek@covenantspc.com'] + email_list[1:]

            subject = f"Inquiry for {product} (CAS: {cas})"
            quantity_info = ', '.join(f"{q} {u}" for q, u in zip(quantities, units))

            # Create HTML body
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <p>Dear Sir/Madam,</p>
                    <p><strong>Greetings from Covenants PharmaChem!</strong></p>
                    <p>Covenants PharmaChem provides Sourcing, Contract Manufacturing, Customs Research, Impurity Synthesis, Small Molecule development services through its 110+ network partners all over India. We have capabilities from Gram to Metric Ton scale for all the complex chemical reactions.</p>
                    <p>For one of our project, we are looking for:</p>


                    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0;">
                        <tr><td style="padding: 8px;"><strong>Product Name</strong></td><td style="padding: 8px;">{product}</td></tr>
                        <tr><td style="padding: 8px;"><strong>CAS Number</strong></td><td style="padding: 8px;">{cas}</td></tr>
                        <tr><td style="padding: 8px;"><strong>Quantity</strong></td><td style="padding: 8px;">{quantity_info}</td></tr>
                        {remarks_row}
                    </table>
                    
                    <p>Request to give your best offer along with lead time, COA/Specs, Packing size & HSN codes.</p>
                    
                    <p>Best regards,<br>Sachin<br>Sourcing Team</p>
                    <p><strong>Covenants PharmaChem LLP</strong><br>
                    Email: info@covenantspc.com<br>
                    Website: www.covenantspc.com<br>
                    Contact no: +91 8452008095 / 93
                    </p>

                    <!-- Logo Centered at Bottom -->
                    <div style="margin-top: 20px; text-align: left;">
                        <img src="cid:logo_cid" alt="Company Logo" style="max-width: 200px; height: auto;">
                    </div>
                </body>
            </html>
            """

            # Create the email
            msg = MIMEMultipart('related')
            msg['Subject'] = subject
            msg['From'] = SENDER_EMAIL
            msg['To'] = primary_recipient
            msg['Cc'] = ', '.join(cc_recipients)

            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            msg_alternative.attach(MIMEText(html, 'html'))

            # Attach logo from static folder
            with open('static/logo_bottom.png', 'rb') as img_file:
                logo = MIMEImage(img_file.read())
                logo.add_header('Content-ID', '<logo_cid>')  # Very important
                logo.add_header('Content-Disposition', 'inline', filename="logo_bottom.png")
                msg.attach(logo)

            # Send the email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                all_recipients = [primary_recipient] + cc_recipients
                server.sendmail(SENDER_EMAIL, all_recipients, msg.as_string())

            # Log inquiry
            log_file = 'logs/inquiries.csv'
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if f.tell() == 0:
                    writer.writerow(['timestamp', 'product_name', 'cas', 'quantities', 'units', 'partner', 'emails'])
                writer.writerow([
                    datetime.now().isoformat(),
                    product,
                    cas,
                    ', '.join(quantities),
                    ', '.join(units),
                    data.get('partner', ''),
                    ', '.join(email_list)
                ])

            success_count += 1

        except Exception as e:
            app.logger.error(f"Bulk email error: {str(e)}")
            failure_count += 1

    return jsonify({
        'message': f'Bulk send completed: {success_count} success, {failure_count} failed.'
    })


@app.route('/dashboard')
def dashboard():
    import calendar

    log_file = 'logs/inquiries.csv'
    if not os.path.exists(log_file):
        flash("No inquiry data found yet.", "error")
        return render_template('dashboard.html', charts_available=False)

    df = pd.read_csv(log_file, parse_dates=['timestamp'])

    if df.empty:
        return render_template('dashboard.html', charts_available=False)

    # Format months like "April 2025"
    df['month'] = df['timestamp'].dt.to_period('M').astype(str)
    monthly_grouped = df.groupby('month').size().sort_index()

    monthly_labels = [
        f"{calendar.month_name[int(m.split('-')[1])]} {m.split('-')[0]}"
        for m in monthly_grouped.index
    ]
    monthly_values = [int(v) for v in monthly_grouped.values]

    # Top products
    top_products = df['product_name'].value_counts().head(5)
    top_products_labels = [str(i).strip() for i in top_products.index]
    top_products_values = [int(v) for v in top_products.values]

    # Top partners
    top_partners = df['partner'].value_counts().head(5)
    top_partners_labels = [str(i).strip() for i in top_partners.index]
    top_partners_values = [int(v) for v in top_partners.values]
    
    # KPIs
    total_inquiries = len(df)
    total_products = df['product_name'].nunique()
    total_partners = df['partner'].nunique()

# Most active month
    most_active_month = monthly_grouped.idxmax()
    most_active_month = f"{calendar.month_name[int(most_active_month.split('-')[1])]} {most_active_month.split('-')[0]}"

    return render_template(
    'dashboard.html',
    charts_available=True,
    monthly_labels=monthly_labels,
    monthly_values=monthly_values,
    top_products_labels=top_products_labels,
    top_products_values=top_products_values,
    top_partners_labels=top_partners_labels,
    top_partners_values=top_partners_values,
    total_inquiries=total_inquiries,
    total_products=total_products,
    total_partners=total_partners,
    most_active_month=most_active_month
)


@app.route('/download_excel')
def download_excel():
    import pandas as pd
    log_file = 'logs/inquiries.csv'
    if not os.path.exists(log_file):
        flash("No data to download", "error")
        return redirect(url_for('dashboard'))

    df = pd.read_csv(log_file)
    output_path = 'logs/inquiry_export.xlsx'
    df.to_excel(output_path, index=False, engine='openpyxl')

    return send_file(output_path, as_attachment=True)

@app.route('/reset_dashboard', methods=['POST'])
def reset_dashboard():
    """Reset the inquiry dashboard"""
    log_file = 'logs/inquiries.csv'
    if os.path.exists(log_file):
        with open(log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'product_name', 'cas', 'quantities', 'units', 'partner', 'emails'])
        return jsonify({'message': 'Dashboard has been reset.'})
    else:
        return jsonify({'message': 'No data file found to reset.'})


if __name__ == '__main__':
    app.run(debug=True)
    # app.run(host="0.0.0.0", port=5000,debug = True)
