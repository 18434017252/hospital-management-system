# Flask Application Setup and Usage Guide

## Overview
This Flask application provides a web interface for the Hospital Management System with routes for patient registration, doctor consultations, billing, and inventory management.

## Prerequisites

### Required Python Packages
```bash
pip install flask pymysql
```

### Database Setup
1. Make sure MySQL server is running
2. Create the database and load the schema:
```bash
mysql -u username -p < hospital_management_system.sql
```

## Configuration

Before running the application, update the database configuration in `app.py`:

```python
DB_CONFIG = {
    'host': 'localhost',        # Your MySQL host
    'user': 'root',             # Your MySQL username
    'password': 'password',     # Your MySQL password
    'db': 'hospital_management' # Your database name
}
```

Also update the secret key for production use:
```python
app.secret_key = 'your-secret-key-here'
```

## Running the Application

1. Navigate to the backend directory:
```bash
cd backend
```

2. Run the Flask application:
```bash
python3 app.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Application Routes

### 1. Home (`/`)
- Entry point for role selection
- Roles: Registrar, Doctor, Admin
- Stores role and user_id in session

### 2. Patient Registration (`/register`)
- **GET**: Display registration form with departments
- **POST**: Register a patient with selected department and doctor
- Redirects to billing page upon success

### 3. Doctor Queue (`/doctor/queue`)
- Shows patients waiting for consultation
- Filtered by logged-in doctor's ID
- Only shows patients with paid registration fee (status=1)

### 4. Diagnosis & Prescription (`/doctor/diagnose/<reg_id>`)
- **GET**: Display patient information for diagnosis
- **POST**: Submit prescriptions with drug details
- Supports multiple drug prescriptions
- Handles inventory errors (out of stock)

### 5. Billing Center (`/billing`)
- **GET**: Search and view unpaid bills by patient ID
- **POST**: Process payment confirmation
- Triggers database updates for registration status and inventory

### 6. Inventory Management (`/admin/inventory`)
- Monitor drug inventory levels
- Configurable stock threshold (default: 10 units)
- Highlights low-stock and out-of-stock items

## Features

### Error Handling
- All database errors are captured and displayed via flash messages
- Try-except blocks on all database modification routes
- Proper error messages for insufficient inventory, duplicate registrations, etc.

### Session Management
- Role-based access control
- User ID stored in session for filtering
- Automatic logout functionality

### Business Logic Integration
- Seamless integration with `HospitalService` class
- All business logic handled by the service layer
- Database operations abstracted through `DatabaseManager`

## API Endpoints

### Get Doctors by Department
```
GET /api/doctors/<dept_id>
```
Returns JSON list of doctors for a specific department.

## User Workflows

### Registrar Workflow
1. Select "Registrar" role on home page
2. Navigate to Registration page
3. Enter patient ID, select department and doctor
4. Submit registration
5. View pending payments in Billing Center
6. Process payments

### Doctor Workflow
1. Select "Doctor" role and enter doctor ID
2. View patient queue
3. Select a patient to diagnose
4. Enter prescriptions (drugs, quantities, dosage)
5. Submit diagnosis

### Admin Workflow
1. Select "Admin" role on home page
2. View inventory dashboard
3. Monitor low-stock items
4. Adjust threshold as needed

## Error Messages

The application provides user-friendly error messages for:
- Database connection failures
- Insufficient drug inventory
- Duplicate registrations
- Invalid input values
- Missing required fields

## Security Notes

⚠️ **Important for Production:**
1. Change the default `secret_key` in `app.py`
2. Use environment variables for sensitive configuration
3. Enable HTTPS
4. Implement proper authentication and authorization
5. Add input validation and sanitization
6. Set `debug=False` in production

## Troubleshooting

### Database Connection Error
- Verify MySQL is running
- Check DB_CONFIG credentials
- Ensure database exists and schema is loaded

### Import Error
- Install required packages: `pip install flask pymysql`
- Ensure `db_util.py` and `hospital_service.py` are in the same directory

### Template Not Found
- Ensure `templates/` directory exists
- Verify all HTML template files are present

## Development

To run in development mode with auto-reload:
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

## License
This project is part of the Hospital Management System and follows the same license terms.
