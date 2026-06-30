# Emmanuel Tech ICT Solutions

A comprehensive web application for ICT service bookings with ticket generation and email confirmations.

## Features

- **Service Booking System**: Book ICT services with detailed descriptions
- **Automatic Ticket Generation**: Unique ticket codes for each booking
- **PDF Ticket Downloads**: Professional PDF receipts with all booking details
- **Email Confirmations**: Automatic email sending with PDF ticket attachments
- **WhatsApp Integration**: Share booking details via WhatsApp
- **Admin Dashboard**: Manage bookings, update status, and generate reports
- **Print Functionality**: Print tickets directly from the browser

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Email Configuration

The application sends automatic email confirmations with PDF ticket attachments.

#### Gmail Setup (Recommended):

1. **Create a .env file** in the project root with your email credentials:
   ```env
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

2. **Generate Gmail App Password**:
   - Go to your Google Account settings
   - Enable 2-Factor Authentication if not already enabled
   - Go to Security → App passwords
   - Generate a password for "Mail"
   - Use this 16-character password as `MAIL_PASSWORD`

3. **Example .env file**:
   ```env
   MAIL_USERNAME=emmanueltechictsolutions@gmail.com
   MAIL_PASSWORD=abcd-efgh-ijkl-mnop
   ```

**Note**: The app will still work without email configuration, but email confirmations won't be sent.

### 3. Run the Application

```bash
python python_backend.py
```

The application will start on `http://127.0.0.1:5001`

### 4. Access the Application

- **Main Site**: `http://127.0.0.1:5001`
- **Admin Panel**: `http://127.0.0.1:5001/admin/login`
  - Username: `admin`
  - Password: `admin123`

## How It Works

### For Customers:

1. **Book a Service**:
   - Fill in your full name, contact (email/phone), select service
   - Choose date and time, describe your issue
   - Submit the booking

2. **Instant Confirmation**:
   - Booking is saved with unique ticket code
   - Confirmation modal appears with booking summary
   - Email is automatically sent (if email provided) with PDF ticket attached

3. **Ticket Options**:
   - **Download PDF**: Save professional ticket receipt
   - **Print**: Print ticket directly
   - **Share via WhatsApp**: Send booking details to WhatsApp

### For Admins:

- View all bookings in the dashboard
- Update booking status and add notes
- Generate reports
- Manage service records

## Email Template

When a booking is confirmed, customers receive an email with:

- Booking confirmation message
- Service details and ticket number
- Status: "in progress"
- PDF ticket attachment
- Contact information for support

## File Structure

```
emmanuel-tech-ict/
├── python_backend.py          # Flask backend with email & PDF functionality
├── index.html                 # Main customer booking page
├── admin_login.html          # Admin login page
├── admin_dashboard.html      # Admin booking management
├── admin_report.html         # Admin reporting interface
├── requirements.txt          # Python dependencies
├── .env                      # Email configuration (create this)
├── emmanuel_tech.db         # SQLite database (auto-created)
└── README.md                # This file
```

## Technologies Used

- **Backend**: Flask (Python)
- **Database**: SQLite
- **PDF Generation**: ReportLab
- **Email**: Flask-Mail with Gmail SMTP
- **Frontend**: HTML, CSS, JavaScript
- **Icons**: Font Awesome

## Security Notes

- Change the default admin credentials in production
- Use environment variables for sensitive data
- Consider using a dedicated email service for production
- The app uses secure session cookies

## Support

For technical support, contact:
- Email: emmanueltechictsolutions@gmail.com
- Phone: 0716205974