# Hospital Management System

A comprehensive database design for a hospital management system with normalized tables, stored procedures, and triggers.

## Database Structure

### Tables (7 normalized tables)

1. **patient** - Stores patient information (name, gender, date of birth, contact details, ID card)
2. **department** - Stores hospital departments (name, description, location, contact)
3. **doctor** - Stores doctor information (name, title, department, specialization)
4. **registration** - Stores patient registration records with `status` field (0:未缴费, 1:待就诊, 2:已完成)
5. **payment** - Stores payment records with `payment_status` field (0:未支付, 1:已支付) and `payment_type` field (Registration:挂号费, Medicine:药费)
6. **drug** - Stores drug inventory (name, specification, stock quantity, price)
7. **prescription** - Stores prescription details (drug, quantity, dosage, duration) with `payment_id` link

### Stored Procedures

1. **`sp_add_patient`**
   - Handles patient creation with phone number uniqueness check
   - Input: `patient_name`, `gender`, `date_of_birth`, `phone`, `address`, `id_card`
   - Output: `patient_id` (existing or newly created)
   - Returns existing patient if phone number matches

2. **`sp_submit_registration`**
   - Creates a registration record and its corresponding registration payment record
   - Input: `patient_id`, `department_id`, `doctor_id`, `payment_method` (optional, defaults to 'Cash')
   - Output: `registration_id`
   - Automatically sets initial status to 0 (未缴费) and creates a 'Registration' type payment with status 0 (未支付)

3. **`sp_create_prescription`**
   - Creates prescription with automatic cost calculation and payment link
   - Input: `registration_id`, `drug_id`, `quantity`, `dosage`, `duration_days`, `notes`, `payment_method`
   - Output: `payment_id`
   - Calculates total cost from drug unit price × quantity
   - Creates 'Medicine' type payment and links it to prescription
   - Updates registration status to 2 (已完成)

4. **`sp_finish_consultation`**
   - Facilitates completion of visit by inserting prescription and pending payment in an atomic transaction
   - Input: `registration_id`, `drug_id`, `quantity`, `dosage`, `duration_days`, `notes`, `payment_method`
   - Output: `payment_id`
   - Wraps `sp_create_prescription` in a transaction with rollback on error

### Triggers

1. **`trig_check_stock_before_prescription`** (BEFORE INSERT on prescription)
   - Validates stock availability before a prescription is created
   - Raises error if stock is insufficient using `SIGNAL SQLSTATE`
   - Prevents prescription creation when inventory cannot fulfill the request

2. **`trig_after_payment_update`** (AFTER UPDATE on payment)
   - Monitors changes to `payment_status` and handles different `payment_type`:
     - **Registration payments**: Updates registration status from 0 to 1 (待就诊) when payment_status changes to 1 (已支付)
     - **Medicine payments**: Depletes drug inventory when payment is fulfilled, raises error if stock levels cannot meet demands
   - Ensures atomic stock reduction with validation to prevent race conditions

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

### Add or Get Patient
```sql
-- Create a new patient (or get existing by phone)
CALL sp_add_patient('张三', 'M', '1985-06-15', '13812345678', '北京市朝阳区', '110101198506151234', @patient_id);
SELECT @patient_id;
```

### Create a New Registration
```sql
-- Create registration with default payment method (Cash)
CALL sp_submit_registration(1, 1, 1, NULL, @reg_id);
SELECT @reg_id;

-- Create registration with specified payment method and doctor
CALL sp_submit_registration(1, 2, 2, 'Card', @reg_id);
SELECT @reg_id;
```

### Process Registration Payment
```sql
-- Update registration payment status to paid (this will trigger status update in registration)
UPDATE payment 
SET payment_status = 1, payment_date = NOW() 
WHERE payment_id = 1 AND payment_type = 'Registration';
```

### Create a Prescription with Payment
```sql
-- Create prescription with automatic cost calculation and medicine payment
CALL sp_create_prescription(1, 1, 2, '1粒，每日3次，饭后服用', 7, '注意过敏反应', 'Cash', @med_payment_id);
SELECT @med_payment_id;
```

### Complete a Consultation
```sql
-- Finish consultation in atomic transaction
CALL sp_finish_consultation(1, 1, 2, '1粒，每日3次', 7, '注意过敏', 'Card', @payment_id);
SELECT @payment_id;
```

### Process Medicine Payment
```sql
-- Pay for medicine (this will automatically reduce drug stock)
UPDATE payment 
SET payment_status = 1, payment_date = NOW() 
WHERE payment_id = @med_payment_id AND payment_type = 'Medicine';
```

### Complete Patient Workflow
```sql
START TRANSACTION;

-- 1. Add/Get patient
CALL sp_add_patient('完整流程测试', 'F', '1988-03-15', '13811112222', '测试地址', '110101198803153333', @patient_id);

-- 2. Submit registration
CALL sp_submit_registration(@patient_id, 1, 1, 'Card', @reg_id);

-- 3. Pay registration fee
UPDATE payment SET payment_status = 1, payment_date = NOW() 
WHERE registration_id = @reg_id AND payment_type = 'Registration';

-- 4. Create prescription after consultation
CALL sp_create_prescription(@reg_id, 1, 2, '1粒，每日3次', 7, '医嘱', 'Cash', @med_payment_id);

-- 5. Pay for medicine (this will reduce stock)
UPDATE payment SET payment_status = 1, payment_date = NOW() 
WHERE payment_id = @med_payment_id;

COMMIT;
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

### Enhanced Payment System
- **Dual Payment Types**: Supports both 'Registration' and 'Medicine' payment types
- **Linked Prescriptions**: Prescriptions are directly linked to their payment records
- **Automatic Cost Calculation**: Medicine costs are calculated automatically from drug prices

### Data Integrity
- Primary key constraints on all tables
- Foreign key constraints with appropriate ON DELETE and ON UPDATE actions
  - `prescription.payment_id` uses ON DELETE SET NULL for data preservation
- NOT NULL constraints on required fields
- CHECK constraints for data validation:
  - `registration.status` must be 0, 1, or 2
  - `payment.payment_status` must be 0 or 1
  - `payment.payment_type` must be 'Registration' or 'Medicine'
  - `drug.unit_price` must be positive
  - `drug.stored_quantity` must be non-negative
  - `prescription.quantity` must be positive
  - `prescription.duration_days` must be positive
  - `registration.fee` and `payment.amount` must be non-negative
- UNIQUE constraints where applicable (e.g., patient.id_card, drug.drug_code)

### Default Values
- `registration.status` defaults to 0 (未缴费)
- `payment.payment_status` defaults to 0 (未支付)
- `drug.stored_quantity` defaults to 0
- Timestamp fields default to CURRENT_TIMESTAMP

### Automated Business Logic
- **Patient Deduplication**: Automatic patient lookup by phone number
- **Transactional Integrity**: Atomic operations for consultation completion
- **Stock Validation**: Pre-prescription stock checking before insertion
- **Smart Stock Management**: Stock reduction tied to medicine payment completion
- **Status Updates**: Automatic registration status updates based on payment type
- **Automatic Record Creation**: Streamlined workflows through stored procedures

## License

This project is licensed under the terms specified in the LICENSE file.