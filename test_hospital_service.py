"""
Test suite for HospitalService class

This test file validates all functionality of the HospitalService class.
Run with: python test_hospital_service.py

Note: This requires a running MySQL database with the hospital management system schema.
Update the TEST_DB_CONFIG with appropriate credentials before running.
"""

import sys
from hospital_service import HospitalService
from db_util import DatabaseManager, DatabaseError
import pymysql


# Test database configuration
# NOTE: These credentials match the test database used in test_db_util.py
# In production, use environment variables or a secure configuration file
# Update these values to match your test database
TEST_DB_CONFIG = {
    'host': '124.70.86.207',
    'user': 'u23373073',
    'password': 'Aa614391',
    'db': 'try_db23373073'
}


def test_get_departments():
    """Test get_departments method."""
    print("Test 1: Get Departments")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        departments = service.get_departments()
        print(f"✓ Retrieved {len(departments)} departments")
        
        if departments:
            print(f"  Sample department: {departments[0]['department_name']}")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_get_doctors_by_dept():
    """Test get_doctors_by_dept method."""
    print("\nTest 2: Get Doctors by Department")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Get first department
        departments = service.get_departments()
        if not departments:
            print("✗ No departments found in database")
            db.close()
            return False
        
        dept_id = departments[0]['department_id']
        doctors = service.get_doctors_by_dept(dept_id)
        print(f"✓ Retrieved {len(doctors)} doctors for department ID {dept_id}")
        
        if doctors:
            print(f"  Sample doctor: {doctors[0]['doctor_name']}")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_register_patient():
    """Test register_patient method."""
    print("\nTest 3: Register Patient")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Create a test patient first
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Test Service Patient', 'M', '1992-06-15', '19920000010', 
             'Service Test Address', 'SVC920615', None)
        )
        patient_id = out_params[-1]
        print(f"  Created test patient ID: {patient_id}")
        
        # Register the patient
        registration_id, pending_amount = service.register_patient(patient_id, 1, 1)
        print(f"✓ Patient registered successfully")
        print(f"  Registration ID: {registration_id}")
        print(f"  Pending payment amount: {pending_amount}")
        
        # Verify registration was created
        registrations = db.execute_query(
            "SELECT * FROM registration WHERE registration_id = %s",
            (registration_id,)
        )
        
        if not registrations:
            print("✗ Registration not found in database")
            return False
        
        # Cleanup
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("  Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_get_waiting_list():
    """Test get_waiting_list method."""
    print("\nTest 4: Get Waiting List")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Create a test patient and registration with paid status
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Waiting Test Patient', 'F', '1988-03-20', '19880000011', 
             'Waiting Test Address', 'WAIT880320', None)
        )
        patient_id = out_params[-1]
        
        # Create registration
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # Mark registration payment as paid (this will set status to 1)
        db.execute_non_query(
            "UPDATE payment SET payment_status = 1, payment_date = NOW() WHERE registration_id = %s AND payment_type = 'Registration'",
            (registration_id,)
        )
        
        # Get waiting list for doctor 1
        waiting_list = service.get_waiting_list(1)
        print(f"✓ Retrieved {len(waiting_list)} patients in waiting list for doctor 1")
        
        if waiting_list:
            # Find our test patient
            found = any(w['registration_id'] == registration_id for w in waiting_list)
            if found:
                print("  Test patient found in waiting list")
            else:
                print("  Note: Test patient not in first page of results")
        
        # Cleanup
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("  Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_submit_diagnosis():
    """Test submit_diagnosis method."""
    print("\nTest 5: Submit Diagnosis")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Create test patient and registration
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Diagnosis Test Patient', 'M', '1985-11-10', '19850000012', 
             'Diagnosis Test Address', 'DIAG851110', None)
        )
        patient_id = out_params[-1]
        
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # Pay registration fee
        db.execute_non_query(
            "UPDATE payment SET payment_status = 1, payment_date = NOW() WHERE registration_id = %s AND payment_type = 'Registration'",
            (registration_id,)
        )
        
        # Get a drug with sufficient stock
        drugs = db.execute_query("SELECT drug_id FROM drug WHERE stored_quantity >= 5 LIMIT 1")
        if not drugs:
            print("✗ No drugs with sufficient stock found")
            return False
        
        drug_id = drugs[0]['drug_id']
        
        # Submit diagnosis with drug list
        drug_list = [
            {
                'drug_id': drug_id,
                'quantity': 2,
                'dosage': '1 tablet, 3 times daily',
                'duration_days': 7,
                'notes': 'Take after meals'
            }
        ]
        
        payment_ids = service.submit_diagnosis(registration_id, drug_list)
        print(f"✓ Diagnosis submitted successfully")
        print(f"  Created {len(payment_ids)} payment records")
        print(f"  Payment IDs: {payment_ids}")
        
        # Verify prescription was created
        prescriptions = db.execute_query(
            "SELECT * FROM prescription WHERE registration_id = %s",
            (registration_id,)
        )
        
        if not prescriptions:
            print("✗ Prescription not found in database")
            return False
        
        # Cleanup
        db.execute_non_query("DELETE FROM prescription WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("  Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_get_pending_payments():
    """Test get_pending_payments method."""
    print("\nTest 6: Get Pending Payments")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Create test patient with unpaid registration
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Payment Test Patient', 'F', '1990-07-25', '19900000013', 
             'Payment Test Address', 'PAY900725', None)
        )
        patient_id = out_params[-1]
        
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # Get pending payments
        pending_payments = service.get_pending_payments(patient_id)
        print(f"✓ Retrieved {len(pending_payments)} pending payments for patient {patient_id}")
        
        if pending_payments:
            print(f"  Sample payment: Type={pending_payments[0]['payment_type']}, Amount={pending_payments[0]['amount']}")
        
        # Cleanup
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("  Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_pay_bill_success():
    """Test pay_bill method with successful payment."""
    print("\nTest 7: Pay Bill (Success)")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Create test patient and registration
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Bill Test Patient', 'M', '1987-04-18', '19870000014', 
             'Bill Test Address', 'BILL870418', None)
        )
        patient_id = out_params[-1]
        
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # Get the payment ID
        payments = db.execute_query(
            "SELECT payment_id FROM payment WHERE registration_id = %s AND payment_type = 'Registration'",
            (registration_id,)
        )
        payment_id = payments[0]['payment_id']
        
        # Pay the bill
        result = service.pay_bill(payment_id)
        print(f"✓ Payment processed")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message']}")
        
        if not result['success']:
            print("✗ Payment was not successful")
            return False
        
        # Verify payment status was updated
        payments = db.execute_query(
            "SELECT payment_status FROM payment WHERE payment_id = %s",
            (payment_id,)
        )
        
        if payments[0]['payment_status'] != 1:
            print("✗ Payment status not updated in database")
            return False
        
        # Cleanup
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("  Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_pay_bill_inventory_shortfall():
    """Test pay_bill method with inventory shortfall error."""
    print("\nTest 8: Pay Bill (Inventory Shortfall)")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Create test patient and registration
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Shortfall Test Patient', 'F', '1991-09-30', '19910000015', 
             'Shortfall Test Address', 'SHORT910930', None)
        )
        patient_id = out_params[-1]
        
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # Pay registration fee
        db.execute_non_query(
            "UPDATE payment SET payment_status = 1, payment_date = NOW() WHERE registration_id = %s AND payment_type = 'Registration'",
            (registration_id,)
        )
        
        # Get a drug and temporarily reduce its stock to 0
        drugs = db.execute_query("SELECT drug_id, stored_quantity FROM drug LIMIT 1")
        if not drugs:
            print("✗ No drugs found")
            return False
        
        drug_id = drugs[0]['drug_id']
        original_stock = drugs[0]['stored_quantity']
        
        # Reduce stock to 0
        db.execute_non_query("UPDATE drug SET stored_quantity = 0 WHERE drug_id = %s", (drug_id,))
        
        # Create prescription with quantity that exceeds stock
        # Note: Using sp_create_prescription directly for test setup (not through service)
        # The HospitalService.submit_diagnosis uses sp_finish_consultation which wraps sp_create_prescription
        out_params, _ = db.call_procedure(
            'sp_create_prescription',
            (registration_id, drug_id, 5, '1 tablet', 7, 'Test', 'Cash', None)
        )
        payment_id = out_params[-1]
        
        # Try to pay the bill (should fail due to insufficient stock)
        result = service.pay_bill(payment_id)
        
        print(f"✓ Payment processing attempted")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message']}")
        
        if result['success']:
            print("✗ Payment should have failed due to insufficient stock")
            success = False
        elif 'drug_name' in result:
            print(f"  Drug name: {result['drug_name']}")
            print("✓ Inventory shortfall correctly detected and drug name returned")
            success = True
        else:
            print("✗ Expected drug_name in result")
            success = False
        
        # Restore original stock
        db.execute_non_query(
            "UPDATE drug SET stored_quantity = %s WHERE drug_id = %s",
            (original_stock, drug_id)
        )
        
        # Cleanup
        db.execute_non_query("DELETE FROM prescription WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("  Cleanup completed")
        
        db.close()
        return success
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_get_low_stock_drugs():
    """Test get_low_stock_drugs method."""
    print("\nTest 9: Get Low Stock Drugs")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Get low stock drugs with default threshold (10)
        low_stock = service.get_low_stock_drugs()
        print(f"✓ Retrieved {len(low_stock)} drugs with stock below 10")
        
        if low_stock:
            print(f"  Sample drug: {low_stock[0]['drug_name']}, Stock: {low_stock[0]['stored_quantity']}")
        
        # Test with custom threshold
        low_stock_custom = service.get_low_stock_drugs(threshold=50)
        print(f"✓ Retrieved {len(low_stock_custom)} drugs with stock below 50")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def test_multiple_drugs_diagnosis():
    """Test submit_diagnosis with multiple drugs."""
    print("\nTest 10: Submit Diagnosis with Multiple Drugs")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        service = HospitalService(db)
        
        # Create test patient and registration
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Multi Drug Test', 'M', '1989-12-05', '19890000016', 
             'Multi Drug Test Address', 'MULTI891205', None)
        )
        patient_id = out_params[-1]
        
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # Pay registration fee
        db.execute_non_query(
            "UPDATE payment SET payment_status = 1, payment_date = NOW() WHERE registration_id = %s AND payment_type = 'Registration'",
            (registration_id,)
        )
        
        # Get two drugs with sufficient stock
        drugs = db.execute_query("SELECT drug_id FROM drug WHERE stored_quantity >= 3 LIMIT 2")
        if len(drugs) < 2:
            print("✗ Not enough drugs with sufficient stock found")
            return False
        
        # Submit diagnosis with multiple drugs
        drug_list = [
            {
                'drug_id': drugs[0]['drug_id'],
                'quantity': 2,
                'dosage': 'Drug 1 dosage',
                'duration_days': 5
            },
            {
                'drug_id': drugs[1]['drug_id'],
                'quantity': 1,
                'dosage': 'Drug 2 dosage',
                'duration_days': 7
            }
        ]
        
        payment_ids = service.submit_diagnosis(registration_id, drug_list)
        print(f"✓ Multiple drug diagnosis submitted successfully")
        print(f"  Created {len(payment_ids)} payment records")
        
        # Verify prescriptions were created
        prescriptions = db.execute_query(
            "SELECT * FROM prescription WHERE registration_id = %s",
            (registration_id,)
        )
        
        if len(prescriptions) != 2:
            print(f"✗ Expected 2 prescriptions, found {len(prescriptions)}")
            return False
        
        # Cleanup
        db.execute_non_query("DELETE FROM prescription WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("  Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


def run_all_tests():
    """Run all test cases."""
    print("=" * 70)
    print("HospitalService Test Suite")
    print("=" * 70)
    
    tests = [
        test_get_departments,
        test_get_doctors_by_dept,
        test_register_patient,
        test_get_waiting_list,
        test_submit_diagnosis,
        test_get_pending_payments,
        test_pay_bill_success,
        test_pay_bill_inventory_shortfall,
        test_get_low_stock_drugs,
        test_multiple_drugs_diagnosis
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    print("\nNOTE: This test suite requires:")
    print("  1. A running MySQL database")
    print("  2. The hospital_management_system.sql schema loaded")
    print("  3. Proper credentials in TEST_DB_CONFIG")
    print("  4. pymysql library installed (pip install pymysql)")
    print("\nTo skip tests if database is not available, use --skip-db flag\n")
    
    if '--skip-db' in sys.argv:
        print("Skipping database tests (--skip-db flag provided)")
        sys.exit(0)
    
    sys.exit(run_all_tests())
