# Chemical Inquiry System

This is a Flask-based web application to manage chemical product inquiries. Users can search chemicals by name or CAS number and send inquiry emails to vendors.

## Features

- Search chemical products by name or CAS number
- Display product details and vendor information
- Send formatted HTML email inquiries
- Store inquiry history in an Excel file
- Automatically update inquiry status when vendors reply

## Technologies Used

- Python
- Flask
- Pandas
- openpyxl
- smtplib
- HTML & Bootstrap (for frontend)

## Getting Started

1. Clone the repository:
git clone https://github.com/SunnyPaththarwala/Chemical_Inquiry_System.git
cd Chemical_Inquiry_System


2. Install dependencies:
pip install -r requirements.txt



3. Run the app:
python app.py


## Folder Structure

- `templates/` – HTML files
- `static/` – CSS/JS files
- `data/` – Excel files for chemicals and inquiries
- `app.py` – Main Flask app
- `utils.py` – Helper functions for email and data handling
