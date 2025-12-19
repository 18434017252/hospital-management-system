"""
Example usage of the HospitalService class.

This script demonstrates how to use the HospitalService for various operations
in the hospital management system.

Update DB_CONFIG with your database credentials before running.
"""

from hospital_service import HospitalService
from db_util import DatabaseManager, DatabaseError
import pymysql


# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'db': 'hospital_management'
}


def example_registration_module():
    """Demonstrate Registration Module functionality."""
    print("=== Registration Module Examples ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        service = HospitalService(db)
        
        # 1. Get all departments
        print("1. Getting all departments:")
        departments = service.get_departments()
        for dept in departments[:3]:  # Show first 3
            print(f"   - {dept['department_name']} (ID: {dept['department_id']})")
        
        # 2. Get doctors by department
        if departments:
            dept_id = departments[0]['department_id']
            print(f"\n2. Getting doctors for department ID {dept_id}:")
            doctors = service.get_doctors_by_dept(dept_id)
            for doctor in doctors[:3]:  # Show first 3
                print(f"   - Dr. {doctor['doctor_name']}, {doctor['title']}")
        
        # 3. Register a patient
        print("\n3. Registering a patient:")
        # First, create or get a patient using sp_add_patient
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Example Patient', 'M', '1990-01-15', '13800000001', 
             'Example Address', 'EX900115', None)
        )
        patient_id = out_params[-1]
        print(f"   Patient ID: {patient_id}")
        
        # Register the patient
        registration_id, pending_amount = service.register_patient(
            patient_id=patient_id,
            dept_id=1,
            doc_id=1
        )
        print(f"   Registration ID: {registration_id}")
        print(f"   Pending payment amount: ${pending_amount}")
        
        # Cleanup (for demo purposes)
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))


def example_doctor_module():
    """Demonstrate Doctor Module functionality."""
    print("\n=== Doctor Module Examples ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        service = HospitalService(db)
        
        # 1. Get waiting list for a doctor
        print("1. Getting waiting list for doctor ID 1:")
        waiting_list = service.get_waiting_list(doctor_id=1)
        print(f"   Found {len(waiting_list)} patients waiting")
        
        if waiting_list:
            for patient in waiting_list[:2]:  # Show first 2
                print(f"   - {patient['patient_name']}, "
                      f"Registration: {patient['registration_date']}, "
                      f"Status: {patient['status']}")
        
        # 2. Submit diagnosis with prescriptions
        # (This example assumes you have a valid registration_id)
        print("\n2. Submitting diagnosis with prescriptions:")
        print("   (Note: This requires a valid registration in 'Waiting' status)")
        
        # Example drug list structure:
        drug_list_example = [
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
        
        print(f"   Example drug list structure:")
        for i, drug in enumerate(drug_list_example, 1):
            print(f"     Drug {i}: ID={drug['drug_id']}, Qty={drug['quantity']}, "
                  f"Dosage='{drug['dosage']}'")


def example_billing_module():
    """Demonstrate Billing Module functionality."""
    print("\n=== Billing Module Examples ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        service = HospitalService(db)
        
        # Create a test scenario for billing
        # 1. Create patient and registration
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Billing Example', 'F', '1985-05-20', '13800000002', 
             'Billing Address', 'BILL850520', None)
        )
        patient_id = out_params[-1]
        
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # 1. Get pending payments
        print("1. Getting pending payments for patient:")
        pending_payments = service.get_pending_payments(patient_id)
        print(f"   Found {len(pending_payments)} pending payments")
        
        for payment in pending_payments:
            print(f"   - Payment ID: {payment['payment_id']}, "
                  f"Type: {payment['payment_type']}, "
                  f"Amount: ${payment['amount']}")
        
        # 2. Pay a bill
        if pending_payments:
            payment_id = pending_payments[0]['payment_id']
            print(f"\n2. Paying bill (Payment ID: {payment_id}):")
            
            try:
                result = service.pay_bill(payment_id)
                print(f"   Success: {result['success']}")
                print(f"   Message: {result['message']}")
                
                if not result['success'] and 'drug_name' in result:
                    print(f"   Drug with shortage: {result['drug_name']}")
                    
            except DatabaseError as e:
                print(f"   Database error: {e}")
        
        # Cleanup
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))


def example_inventory_module():
    """Demonstrate Inventory Module functionality."""
    print("\n=== Inventory Module Examples ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        service = HospitalService(db)
        
        # 1. Get low stock drugs with default threshold
        print("1. Getting drugs with stock below 10:")
        low_stock = service.get_low_stock_drugs()
        print(f"   Found {len(low_stock)} drugs with low stock")
        
        for drug in low_stock[:5]:  # Show first 5
            print(f"   - {drug['drug_name']}: {drug['stored_quantity']} units "
                  f"(${drug['unit_price']} each)")
        
        # 2. Get low stock drugs with custom threshold
        print("\n2. Getting drugs with stock below 50:")
        low_stock_custom = service.get_low_stock_drugs(threshold=50)
        print(f"   Found {len(low_stock_custom)} drugs below threshold")


def example_error_handling():
    """Demonstrate error handling with HospitalService."""
    print("\n=== Error Handling Examples ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        service = HospitalService(db)
        
        print("1. Handling inventory shortfall during bill payment:")
        print("   When paying for medicine, if inventory is insufficient,")
        print("   the error will include the specific drug name:")
        print()
        print("   try:")
        print("       result = service.pay_bill(payment_id)")
        print("       if not result['success'] and 'drug_name' in result:")
        print("           print(f'Insufficient stock for: {result['drug_name']}')")
        print("   except DatabaseError as e:")
        print("       print(f'Database error: {e}')")
        
        print("\n2. Handling insufficient stock during diagnosis:")
        print("   If prescribed drug quantity exceeds available stock,")
        print("   a DatabaseError will be raised with details:")
        print()
        print("   try:")
        print("       payment_ids = service.submit_diagnosis(reg_id, drug_list)")
        print("   except DatabaseError as e:")
        print("       print(f'Prescription failed: {e}')")
        print("       # Error message includes drug name and quantities")


def example_complete_workflow():
    """Demonstrate a complete patient workflow."""
    print("\n=== Complete Patient Workflow ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        service = HospitalService(db)
        
        try:
            # Step 1: Add/Get patient
            print("Step 1: Adding patient...")
            out_params, _ = db.call_procedure(
                'sp_add_patient',
                ('Workflow Patient', 'M', '1988-03-15', '13800000003', 
                 'Workflow Address', 'FLOW880315', None)
            )
            patient_id = out_params[-1]
            print(f"   Patient ID: {patient_id}")
            
            # Step 2: Register patient
            print("\nStep 2: Registering patient...")
            registration_id, pending_amount = service.register_patient(patient_id, 1, 1)
            print(f"   Registration ID: {registration_id}")
            print(f"   Pending amount: ${pending_amount}")
            
            # Step 3: Check pending payments
            print("\nStep 3: Checking pending payments...")
            pending = service.get_pending_payments(patient_id)
            print(f"   Found {len(pending)} pending payments")
            
            # Step 4: Pay registration fee
            print("\nStep 4: Paying registration fee...")
            reg_payment = [p for p in pending if p['payment_type'] == 'Registration'][0]
            result = service.pay_bill(reg_payment['payment_id'])
            print(f"   Payment successful: {result['success']}")
            
            # Step 5: Check waiting list (doctor's view)
            print("\nStep 5: Checking doctor's waiting list...")
            waiting = service.get_waiting_list(1)
            print(f"   Doctor has {len(waiting)} patients waiting")
            
            # Step 6: Submit diagnosis
            print("\nStep 6: Submitting diagnosis...")
            # Get a drug with sufficient stock
            drugs = db.execute_query("SELECT drug_id FROM drug WHERE stored_quantity >= 5 LIMIT 1")
            if drugs:
                drug_list = [
                    {
                        'drug_id': drugs[0]['drug_id'],
                        'quantity': 2,
                        'dosage': '1 tablet, twice daily',
                        'duration_days': 7
                    }
                ]
                payment_ids = service.submit_diagnosis(registration_id, drug_list)
                print(f"   Created {len(payment_ids)} prescription payment(s)")
                
                # Step 7: Pay medicine fee
                print("\nStep 7: Paying medicine fee...")
                result = service.pay_bill(payment_ids[0])
                print(f"   Payment successful: {result['success']}")
            
            print("\n✓ Complete workflow finished successfully!")
            
            # Cleanup
            print("\nCleaning up test data...")
            db.execute_non_query("DELETE FROM prescription WHERE registration_id = %s", (registration_id,))
            db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
            db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
            db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
            
        except DatabaseError as e:
            print(f"\n✗ Database error occurred: {e}")
        except pymysql.Error as e:
            print(f"\n✗ Database connection error: {e}")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")


def main():
    """Run all examples."""
    print("=" * 70)
    print("HospitalService Usage Examples")
    print("=" * 70)
    print("\nUpdate DB_CONFIG with your database credentials before running!\n")
    
    try:
        example_registration_module()
        example_doctor_module()
        example_billing_module()
        example_inventory_module()
        example_error_handling()
        example_complete_workflow()
        
        print("\n" + "=" * 70)
        print("All examples completed!")
        print("=" * 70)
        
    except pymysql.Error as e:
        print(f"\n✗ Database connection error: {e}")
        print("\nPlease check:")
        print("  1. Database server is running")
        print("  2. Credentials in DB_CONFIG are correct")
        print("  3. hospital_management database exists and schema is loaded")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == '__main__':
    main()
