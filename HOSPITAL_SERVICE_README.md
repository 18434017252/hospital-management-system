# Hospital Service Module

A Python business logic module for the hospital management system that provides high-level operations for patient registration, doctor consultations, billing, and inventory management.

## Overview

The `HospitalService` class provides a clean, intuitive interface for managing hospital operations. It wraps the `DatabaseManager` from `db_util.py` to provide domain-specific methods for common hospital workflows.

## Features

- **Registration Module**: Manage departments, doctors, and patient registrations
- **Doctor Module**: Handle patient waiting lists and diagnosis submissions
- **Billing Module**: Process payments and handle inventory shortfalls
- **Inventory Module**: Monitor drug stock levels for pharmacy alerts
- **Comprehensive Error Handling**: Graceful handling of database constraints and business logic errors

## Installation

### Prerequisites

```bash
pip install pymysql
```

### Files

- `hospital_service.py` - Main service module
- `test_hospital_service.py` - Comprehensive test suite
- `example_hospital_service.py` - Usage examples and demonstrations

## Usage

### Basic Setup

```python
from hospital_service import HospitalService
from db_util import DatabaseManager, DatabaseError

# Configure database connection
config = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'db': 'hospital_management'
}

# Create database manager and service
db = DatabaseManager(config)
service = HospitalService(db)
```

### Using Context Manager

```python
with DatabaseManager(config) as db:
    service = HospitalService(db)
    departments = service.get_departments()
    # Service automatically closes when exiting the with block
```

## API Reference

### Registration Module

#### `get_departments() -> List[Dict[str, Any]]`

Fetch all departments from the database.

```python
departments = service.get_departments()
for dept in departments:
    print(f"{dept['department_name']}: {dept['location']}")
```

**Returns:**
- List of dictionaries containing department information

**Raises:**
- `pymysql.Error`: If database query fails

#### `get_doctors_by_dept(dept_id: int) -> List[Dict[str, Any]]`

Fetch doctors based on department ID.

```python
doctors = service.get_doctors_by_dept(dept_id=1)
for doctor in doctors:
    print(f"Dr. {doctor['doctor_name']}, {doctor['title']}")
```

**Parameters:**
- `dept_id`: Department ID to filter doctors

**Returns:**
- List of dictionaries containing doctor information

**Raises:**
- `pymysql.Error`: If database query fails

#### `register_patient(patient_id: int, dept_id: int, doc_id: int) -> Tuple[int, float]`

Register a patient by calling the stored procedure `sp_submit_registration`.

```python
registration_id, pending_amount = service.register_patient(
    patient_id=123,
    dept_id=1,
    doc_id=5
)
print(f"Registration ID: {registration_id}")
print(f"Pending payment: ${pending_amount}")
```

**Parameters:**
- `patient_id`: Patient ID
- `dept_id`: Department ID
- `doc_id`: Doctor ID

**Returns:**
- Tuple of (registration_id, pending_payment_amount)

**Raises:**
- `DatabaseError`: If database raises custom error
- `pymysql.Error`: If database operation fails

**Note:** The stored procedure in the database is named `sp_submit_registration`.

### Doctor Module

#### `get_waiting_list(doctor_id: int) -> List[Dict[str, Any]]`

Query patients waiting under a specific doctor where status is 1 ('Awaiting Check'/待就诊) and the registration fee has been paid.

```python
waiting_patients = service.get_waiting_list(doctor_id=1)
for patient in waiting_patients:
    print(f"{patient['patient_name']} - {patient['registration_time']}")
```

**Parameters:**
- `doctor_id`: Doctor ID to filter patients

**Returns:**
- List of dictionaries containing patient registration information with:
  - registration_id
  - patient_id
  - patient_name
  - gender
  - phone
  - registration_date
  - registration_time
  - chief_complaint
  - status

**Raises:**
- `pymysql.Error`: If database query fails

#### `submit_diagnosis(reg_id: int, drug_list: List[Dict[str, Any]]) -> List[int]`

Submit diagnosis for a patient with a list of prescribed drugs. Calls the stored procedure `sp_finish_consultation` for each drug.

```python
drug_list = [
    {
        'drug_id': 1,
        'quantity': 2,
        'dosage': '1 tablet, 3 times daily after meals',
        'duration_days': 7,
        'notes': 'Complete the full course'
    },
    {
        'drug_id': 2,
        'quantity': 1,
        'dosage': '2 tablets before bedtime',
        'duration_days': 5,
        'notes': 'May cause drowsiness'
    }
]

payment_ids = service.submit_diagnosis(registration_id, drug_list)
print(f"Created {len(payment_ids)} payment records")
```

**Parameters:**
- `reg_id`: Registration ID
- `drug_list`: List of dictionaries containing:
  - `drug_id` (required): Drug ID
  - `quantity` (required): Quantity to prescribe
  - `dosage` (optional): Dosage instructions, defaults to '按医嘱'
  - `duration_days` (optional): Duration in days, defaults to 7
  - `notes` (optional): Additional notes, defaults to ''

**Returns:**
- List of payment IDs created for each prescription

**Raises:**
- `DatabaseError`: If database raises custom error (e.g., insufficient stock)
- `pymysql.Error`: If database operation fails

### Billing Module

#### `get_pending_payments(patient_id: int) -> List[Dict[str, Any]]`

Fetch all unpaid bills for a specific patient.

```python
pending_payments = service.get_pending_payments(patient_id=123)
for payment in pending_payments:
    print(f"Payment ID: {payment['payment_id']}, "
          f"Type: {payment['payment_type']}, "
          f"Amount: ${payment['amount']}")
```

**Parameters:**
- `patient_id`: Patient ID

**Returns:**
- List of dictionaries containing unpaid payment information with:
  - payment_id
  - registration_id
  - payment_type ('Registration' or 'Medicine')
  - amount
  - payment_method
  - payment_status
  - registration_date
  - doctor_id
  - doctor_name

**Raises:**
- `pymysql.Error`: If database query fails

#### `pay_bill(payment_id: int) -> Dict[str, Any]`

Mark a payment as paid (change payment_status to 1). This operation may trigger inventory deduction for medicine payments. If there is insufficient stock, the error will include specific drug names.

```python
result = service.pay_bill(payment_id=456)
if result['success']:
    print("Payment successful!")
else:
    print(f"Payment failed: {result['message']}")
    if 'drug_name' in result:
        print(f"Insufficient stock for: {result['drug_name']}")
```

**Parameters:**
- `payment_id`: Payment ID to mark as paid

**Returns:**
- Dictionary with result information:
  - `success` (bool): Indicating success
  - `message` (str): Success or error message
  - `drug_name` (str, optional): Drug name if inventory shortfall occurred
  - `error_type` (str, optional): 'inventory_shortfall' if stock is insufficient

**Raises:**
- `DatabaseError`: If inventory shortfall or other custom database error occurs (for non-inventory errors)
- `pymysql.Error`: If database operation fails

**Special Handling:**
- For inventory shortfalls, returns a dictionary with `success=False` and includes `drug_name` and `error_type`
- This allows the frontend to display user-friendly error messages with specific drug information

### Inventory Module

#### `get_low_stock_drugs(threshold: int = 10) -> List[Dict[str, Any]]`

Fetch drugs with inventory lower than the specified threshold. This is useful for pharmacy alerts to restock drugs.

```python
# Get drugs with stock below default threshold (10)
low_stock = service.get_low_stock_drugs()

# Get drugs with stock below custom threshold
low_stock = service.get_low_stock_drugs(threshold=50)

for drug in low_stock:
    print(f"{drug['drug_name']}: {drug['stored_quantity']} units remaining")
```

**Parameters:**
- `threshold` (optional): Stock quantity threshold, defaults to 10

**Returns:**
- List of dictionaries containing drug information with:
  - drug_id
  - drug_name
  - drug_code
  - specification
  - unit_price
  - stored_quantity

**Raises:**
- `pymysql.Error`: If database query fails

## Error Handling

The `HospitalService` module provides comprehensive error handling:

### DatabaseError (Custom Exceptions)

User-defined database errors (SQLSTATE 45000) from triggers and stored procedures:

```python
try:
    payment_ids = service.submit_diagnosis(reg_id, drug_list)
except DatabaseError as e:
    print(f"Business logic error: {e}")
    # Handle errors like insufficient stock during prescription
```

### Inventory Shortfall Handling

Special handling for inventory shortages during payment processing:

```python
result = service.pay_bill(payment_id)
if not result['success']:
    if 'drug_name' in result and result.get('error_type') == 'inventory_shortfall':
        print(f"Cannot process payment: Insufficient stock for {result['drug_name']}")
        print(f"Details: {result['message']}")
    else:
        print(f"Payment failed: {result['message']}")
```

### Database Errors

Standard database errors (connection issues, constraint violations, etc.):

```python
try:
    departments = service.get_departments()
except pymysql.Error as e:
    print(f"Database error: {e}")
    # Handle connection errors, query failures, etc.
```

## Complete Workflow Example

```python
from hospital_service import HospitalService
from db_util import DatabaseManager, DatabaseError
import pymysql

config = {
    'host': 'localhost',
    'user': 'user',
    'password': 'password',
    'db': 'hospital_management'
}

with DatabaseManager(config) as db:
    service = HospitalService(db)
    
    try:
        # 1. Add/Get patient
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('John Doe', 'M', '1985-06-15', '13812345678', 
             'Address', 'ID123456', None)
        )
        patient_id = out_params[-1]
        
        # 2. Register patient
        registration_id, pending_amount = service.register_patient(patient_id, 1, 1)
        print(f"Registration created: {registration_id}, Amount due: ${pending_amount}")
        
        # 3. Check and pay registration fee
        pending = service.get_pending_payments(patient_id)
        reg_payment = [p for p in pending if p['payment_type'] == 'Registration'][0]
        result = service.pay_bill(reg_payment['payment_id'])
        
        # 4. Doctor checks waiting list
        waiting = service.get_waiting_list(doctor_id=1)
        print(f"Patients waiting: {len(waiting)}")
        
        # 5. Submit diagnosis with prescriptions
        drug_list = [
            {'drug_id': 1, 'quantity': 2, 'dosage': '1 tablet, 3 times daily', 'duration_days': 7}
        ]
        payment_ids = service.submit_diagnosis(registration_id, drug_list)
        
        # 6. Pay medicine fee
        result = service.pay_bill(payment_ids[0])
        if result['success']:
            print("Treatment completed successfully!")
        else:
            print(f"Payment failed: {result['message']}")
            
    except DatabaseError as e:
        print(f"Business logic error: {e}")
    except pymysql.Error as e:
        print(f"Database error: {e}")
```

## Testing

Run the comprehensive test suite:

```bash
python test_hospital_service.py
```

To skip tests if database is not available:

```bash
python test_hospital_service.py --skip-db
```

## Examples

Run the example script to see all features in action:

```bash
python example_hospital_service.py
```

Make sure to update the `DB_CONFIG` in the example file with your database credentials.

## Notes

1. **Stored Procedure Names**: The specification mentions `sp_create_registration`, but the actual stored procedure in the database is `sp_submit_registration`. The `HospitalService` uses the correct name `sp_submit_registration`.

2. **Transaction Management**: The service relies on the `DatabaseManager` for transaction management. All operations that modify data (registration, diagnosis, payments) are automatically committed or rolled back on error.

3. **Inventory Shortfalls**: When paying for medicine, if there is insufficient stock, the `pay_bill` method returns a dictionary with `success=False` and includes the `drug_name` for user-friendly error messages. This is not raised as an exception to allow the frontend to handle it gracefully.

4. **Default Values**: The `submit_diagnosis` method uses sensible defaults:
   - `dosage`: '按医嘱' (according to doctor's advice)
   - `duration_days`: 7
   - `notes`: '' (empty string)

## Best Practices

1. **Use Context Manager**: Always use the `with` statement with `DatabaseManager` to ensure connections are properly closed:
   ```python
   with DatabaseManager(config) as db:
       service = HospitalService(db)
       # Your code here
   ```

2. **Handle Errors Gracefully**: Distinguish between business logic errors (DatabaseError) and database errors:
   ```python
   try:
       result = service.some_operation()
   except DatabaseError as e:
       # Handle business logic errors
   except pymysql.Error as e:
       # Handle database errors
   ```

3. **Check Return Values**: Always check the `success` field in return dictionaries:
   ```python
   result = service.pay_bill(payment_id)
   if not result['success']:
       # Handle failure
   ```

4. **Validate Input**: Ensure patient IDs, department IDs, doctor IDs, and drug IDs are valid before calling service methods.

5. **Monitor Inventory**: Use `get_low_stock_drugs()` regularly to alert pharmacy staff about low stock levels.

## License

This module is part of the Hospital Management System project. See LICENSE file for details.
