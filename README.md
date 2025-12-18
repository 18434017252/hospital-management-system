# Hospital Management System

A comprehensive database design for a hospital management system with normalized tables, stored procedures, and triggers.

## Database Structure

### Tables (7 normalized tables)

1. **patient** - Stores patient information (name, gender, date of birth, contact details, ID card)
2. **department** - Stores hospital departments (name, description, location, contact)
3. **doctor** - Stores doctor information (name, title, department, specialization)
4. **registration** - Stores patient registration records with `status` field (0:未缴费, 1:待就诊, 2:已完成)
5. **payment** - Stores payment records with `payment_status` field (0:未支付, 1:已支付)
6. **drug** - Stores drug inventory (name, specification, stock quantity, price)
7. **prescription** - Stores prescription details (drug, quantity, dosage, duration)

### Stored Procedure

**`sp_create_registration`**
- Creates a registration record and its corresponding payment record
- Input: `patient_id`, `department_id`
- Output: `registration_id`
- Automatically sets initial status to 0 (未缴费) and payment_status to 0 (未支付)

### Triggers

1. **`trig_reduce_stock`** (AFTER INSERT on prescription)
   - Automatically reduces drug stock when a prescription is created
   - Raises error if stock is insufficient using `SIGNAL SQLSTATE`

2. **`trig_update_reg_status`** (AFTER UPDATE on payment)
   - Automatically updates registration status from 0 to 1 (待就诊) when payment_status changes to 1 (已支付)

## Installation

### Prerequisites
- MySQL 5.7+ or MariaDB 10.2+

### Setup

1. Create a database:
```sql
CREATE DATABASE hospital_management;
```

2. Execute the SQL script:
```bash
mysql -u username -p hospital_management < hospital_management_system.sql
```

## Usage Examples

### Create a New Registration
```sql
-- Create registration and get the registration_id
CALL sp_create_registration(1, 1, @new_reg_id);
SELECT @new_reg_id;
```

### Process Payment
```sql
-- Update payment status to paid (this will trigger status update in registration)
UPDATE payment 
SET payment_status = 1, payment_date = NOW() 
WHERE payment_id = 1;
```

### Create a Prescription
```sql
-- Add prescription (this will automatically reduce drug stock)
INSERT INTO prescription (registration_id, drug_id, quantity, dosage, duration_days)
VALUES (1, 1, 2, '1粒，每日3次，饭后服用', 7);
```

## Test Data

The SQL script includes test data for all tables with logical relationships:
- 5 patients
- 5 departments (内科, 外科, 儿科, 妇产科, 骨科)
- 5 doctors (assigned to different departments)
- 5 registrations (with initial status 0)
- 5 payment records (with initial payment_status 0)
- 5 drugs (with stock quantities)

## Features

### Data Integrity
- Primary key constraints on all tables
- Foreign key constraints with appropriate ON DELETE and ON UPDATE actions
- NOT NULL constraints on required fields
- CHECK constraints for data validation
- UNIQUE constraints where applicable

### Default Values
- `registration.status` defaults to 0 (未缴费)
- `payment.payment_status` defaults to 0 (未支付)
- `drug.stored_quantity` defaults to 0
- Timestamp fields default to CURRENT_TIMESTAMP

### Automated Business Logic
- Stock management through triggers
- Status updates through triggers
- Automatic record creation through stored procedures

## License

This project is licensed under the terms specified in the LICENSE file.