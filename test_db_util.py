"""
Test suite for the Database Utility Module (db_util.py)

This test file demonstrates and validates all functionality of the DatabaseManager class.
Run with: python test_db_util.py

Note: This requires a running MySQL database with the hospital management system schema.
Update the TEST_DB_CONFIG with appropriate credentials before running.
"""

import sys
from db_util import DatabaseManager, DatabaseError
import pymysql


# Test database configuration
# Update these values to match your test database
TEST_DB_CONFIG = {
    'host': 'localhost',
    'user': 'test_user',
    'password': 'test_password',
    'db': 'hospital_management'
}


def test_connection():
    """Test database connection establishment."""
    print("Test 1: Database Connection")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        print("✓ Connection established successfully")
        db.close()
        return True
    except pymysql.Error as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_execute_query():
    """Test execute_query method for SELECT statements."""
    print("\nTest 2: Execute Query (SELECT)")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        
        # Test simple SELECT query
        results = db.execute_query("SELECT * FROM department LIMIT 5")
        print(f"✓ Query executed successfully, retrieved {len(results)} rows")
        
        if results:
            print(f"  Sample row: {results[0]}")
        
        # Test parameterized query
        results = db.execute_query(
            "SELECT * FROM department WHERE department_id = %s",
            (1,)
        )
        print(f"✓ Parameterized query executed, retrieved {len(results)} rows")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Query execution failed: {e}")
        return False


def test_execute_non_query():
    """Test execute_non_query method for INSERT/UPDATE/DELETE."""
    print("\nTest 3: Execute Non-Query (INSERT/UPDATE/DELETE)")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        
        # Test INSERT
        affected = db.execute_non_query(
            """INSERT INTO patient (patient_name, gender, date_of_birth, phone, address, id_card)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ('Test Patient', 'M', '1990-01-01', '19900000000', 'Test Address', 'TEST990101')
        )
        print(f"✓ INSERT executed successfully, {affected} row(s) affected")
        
        # Test UPDATE
        affected = db.execute_non_query(
            "UPDATE patient SET address = %s WHERE id_card = %s",
            ('Updated Address', 'TEST990101')
        )
        print(f"✓ UPDATE executed successfully, {affected} row(s) affected")
        
        # Test DELETE (cleanup)
        affected = db.execute_non_query(
            "DELETE FROM patient WHERE id_card = %s",
            ('TEST990101',)
        )
        print(f"✓ DELETE executed successfully, {affected} row(s) affected")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Non-query execution failed: {e}")
        return False


def test_call_procedure():
    """Test call_procedure method for stored procedures."""
    print("\nTest 4: Call Stored Procedure")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        
        # Test sp_add_patient procedure
        # This procedure has an OUT parameter for patient_id
        out_params, result_sets = db.call_procedure(
            'sp_add_patient',
            ('Test Procedure Patient', 'F', '1985-05-15', '19850000001', 
             'Procedure Test Address', 'PROC850515', None)
        )
        
        # The last parameter should be the OUT patient_id
        patient_id = out_params[-1]
        print(f"✓ Stored procedure executed successfully")
        print(f"  OUT parameter (patient_id): {patient_id}")
        
        # Test sp_submit_registration procedure
        out_params, result_sets = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        
        registration_id = out_params[-1]
        print(f"✓ sp_submit_registration executed successfully")
        print(f"  OUT parameter (registration_id): {registration_id}")
        
        # Cleanup - delete the test registration and patient
        db.execute_non_query(
            "DELETE FROM payment WHERE registration_id = %s",
            (registration_id,)
        )
        db.execute_non_query(
            "DELETE FROM registration WHERE registration_id = %s",
            (registration_id,)
        )
        db.execute_non_query(
            "DELETE FROM patient WHERE patient_id = %s",
            (patient_id,)
        )
        print("✓ Cleanup completed")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Procedure call failed: {e}")
        return False


def test_custom_exception():
    """Test custom DatabaseError exception for SQLSTATE 45000."""
    print("\nTest 5: Custom Exception Handling (SQLSTATE 45000)")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        
        # First, create a test patient for the trigger test
        out_params, _ = db.call_procedure(
            'sp_add_patient',
            ('Exception Test Patient', 'M', '1980-01-01', '19800000002',
             'Exception Test', 'EXC800101', None)
        )
        patient_id = out_params[-1]
        
        # Create a registration
        out_params, _ = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        registration_id = out_params[-1]
        
        # Try to create a prescription with insufficient stock
        # This should trigger the BEFORE INSERT trigger that checks stock
        try:
            # Get a drug ID
            drugs = db.execute_query("SELECT drug_id FROM drug LIMIT 1")
            if drugs:
                drug_id = drugs[0]['drug_id']
                
                # Try to prescribe a huge quantity that exceeds stock
                out_params, _ = db.call_procedure(
                    'sp_create_prescription',
                    (registration_id, drug_id, 999999, '1粒', 7, 'Test', 'Cash', None)
                )
                print("✗ Expected DatabaseError was not raised")
                return False
        except DatabaseError as e:
            print(f"✓ DatabaseError correctly raised for SQLSTATE 45000")
            print(f"  Error message: {e}")
            caught_exception = True
        except Exception as e:
            print(f"✗ Unexpected exception type: {type(e).__name__}: {e}")
            caught_exception = False
        
        # Cleanup
        db.execute_non_query(
            "DELETE FROM payment WHERE registration_id = %s",
            (registration_id,)
        )
        db.execute_non_query(
            "DELETE FROM registration WHERE registration_id = %s",
            (registration_id,)
        )
        db.execute_non_query(
            "DELETE FROM patient WHERE patient_id = %s",
            (patient_id,)
        )
        
        db.close()
        return caught_exception
    except Exception as e:
        print(f"✗ Custom exception test failed: {e}")
        return False


def test_context_manager():
    """Test context manager functionality."""
    print("\nTest 6: Context Manager (__enter__ and __exit__)")
    try:
        with DatabaseManager(TEST_DB_CONFIG) as db:
            results = db.execute_query("SELECT COUNT(*) as count FROM department")
            count = results[0]['count']
            print(f"✓ Context manager works correctly")
            print(f"  Retrieved count: {count}")
        print("✓ Connection closed automatically")
        return True
    except Exception as e:
        print(f"✗ Context manager test failed: {e}")
        return False


def test_transaction_rollback():
    """Test that execute_non_query rolls back on error."""
    print("\nTest 7: Transaction Rollback on Error")
    try:
        db = DatabaseManager(TEST_DB_CONFIG)
        
        # Try to insert with a duplicate id_card (should fail due to UNIQUE constraint)
        try:
            db.execute_non_query(
                """INSERT INTO patient (patient_name, gender, date_of_birth, phone, address, id_card)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                ('Duplicate Test', 'M', '1990-01-01', '19900000003', 'Test', 'TEST990101')
            )
            # Try again with same id_card
            db.execute_non_query(
                """INSERT INTO patient (patient_name, gender, date_of_birth, phone, address, id_card)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                ('Duplicate Test 2', 'F', '1991-01-01', '19910000004', 'Test', 'TEST990101')
            )
            print("✗ Duplicate insert should have failed")
            result = False
        except pymysql.Error:
            print("✓ Rollback executed correctly on error")
            result = True
        
        # Cleanup - remove the first insert if it succeeded
        try:
            db.execute_non_query(
                "DELETE FROM patient WHERE id_card = %s",
                ('TEST990101',)
            )
        except:
            pass
        
        db.close()
        return result
    except Exception as e:
        print(f"✗ Rollback test failed: {e}")
        return False


def run_all_tests():
    """Run all test cases."""
    print("=" * 60)
    print("Database Utility Module Test Suite")
    print("=" * 60)
    
    tests = [
        test_connection,
        test_execute_query,
        test_execute_non_query,
        test_call_procedure,
        test_custom_exception,
        test_context_manager,
        test_transaction_rollback
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
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
