"""
Example usage of the DatabaseManager class from db_util module.

This script demonstrates how to use the DatabaseManager for various operations.
"""

from db_util import DatabaseManager, DatabaseError
import pymysql


# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'db': 'hospital_management'
}


def example_basic_usage():
    """Demonstrate basic DatabaseManager usage."""
    print("=== Basic Usage Example ===\n")
    
    # Create a database manager instance
    db = DatabaseManager(DB_CONFIG)
    
    # Example 1: Execute a SELECT query
    print("1. Executing SELECT query:")
    departments = db.execute_query("SELECT * FROM department LIMIT 3")
    for dept in departments:
        print(f"   - {dept['department_name']}: {dept['location']}")
    
    # Example 2: Execute a parameterized query
    print("\n2. Executing parameterized query:")
    dept = db.execute_query(
        "SELECT * FROM department WHERE department_id = %s",
        (1,)
    )
    if dept:
        print(f"   Found: {dept[0]['department_name']}")
    
    db.close()


def example_context_manager():
    """Demonstrate context manager usage."""
    print("\n=== Context Manager Example ===\n")
    
    # Using with statement ensures connection is closed automatically
    with DatabaseManager(DB_CONFIG) as db:
        results = db.execute_query("SELECT COUNT(*) as count FROM patient")
        print(f"Total patients: {results[0]['count']}")
    
    print("Connection closed automatically")


def example_insert_update_delete():
    """Demonstrate INSERT, UPDATE, and DELETE operations."""
    print("\n=== INSERT/UPDATE/DELETE Example ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        # INSERT
        print("1. Inserting a new patient:")
        affected = db.execute_non_query(
            """INSERT INTO patient (patient_name, gender, date_of_birth, phone, address, id_card)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ('Example Patient', 'M', '1995-03-20', '13800000000', 'Example Address', 'EXAMPLE123')
        )
        print(f"   Inserted {affected} row(s)")
        
        # UPDATE
        print("\n2. Updating patient address:")
        affected = db.execute_non_query(
            "UPDATE patient SET address = %s WHERE id_card = %s",
            ('New Address', 'EXAMPLE123')
        )
        print(f"   Updated {affected} row(s)")
        
        # DELETE
        print("\n3. Deleting the patient:")
        affected = db.execute_non_query(
            "DELETE FROM patient WHERE id_card = %s",
            ('EXAMPLE123',)
        )
        print(f"   Deleted {affected} row(s)")


def example_stored_procedure():
    """Demonstrate calling stored procedures."""
    print("\n=== Stored Procedure Example ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        # Call sp_add_patient procedure
        print("1. Calling sp_add_patient:")
        out_params, result_sets = db.call_procedure(
            'sp_add_patient',
            ('Procedure Example', 'F', '1988-08-08', '13900000001', 'Proc Address', 'PROC880808', None)
        )
        
        # Extract the OUT parameter (patient_id)
        patient_id = out_params[-1]
        print(f"   Created/Found patient with ID: {patient_id}")
        
        # Call sp_submit_registration procedure
        print("\n2. Calling sp_submit_registration:")
        out_params, result_sets = db.call_procedure(
            'sp_submit_registration',
            (patient_id, 1, 1, 'Cash', None)
        )
        
        registration_id = out_params[-1]
        print(f"   Created registration with ID: {registration_id}")
        
        # Cleanup
        print("\n3. Cleaning up test data:")
        db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
        db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
        print("   Cleanup completed")


def example_error_handling():
    """Demonstrate error handling with custom exceptions."""
    print("\n=== Error Handling Example ===\n")
    
    with DatabaseManager(DB_CONFIG) as db:
        try:
            # Try to create a prescription with insufficient stock
            # This will trigger the database trigger that raises SQLSTATE 45000
            
            # First create necessary records
            out_params, _ = db.call_procedure(
                'sp_add_patient',
                ('Error Test', 'M', '1990-01-01', '13900000002', 'Test', 'ERROR123', None)
            )
            patient_id = out_params[-1]
            
            out_params, _ = db.call_procedure(
                'sp_submit_registration',
                (patient_id, 1, 1, 'Cash', None)
            )
            registration_id = out_params[-1]
            
            # Get a drug ID
            drugs = db.execute_query("SELECT drug_id FROM drug LIMIT 1")
            if drugs:
                drug_id = drugs[0]['drug_id']
                
                # Try to prescribe excessive quantity (will fail due to stock check)
                print("Attempting to prescribe quantity that exceeds stock...")
                out_params, _ = db.call_procedure(
                    'sp_create_prescription',
                    (registration_id, drug_id, 999999, 'Test dosage', 7, 'Test', 'Cash', None)
                )
                
        except DatabaseError as e:
            # This is our custom exception for SQLSTATE 45000 errors
            print(f"✓ Caught DatabaseError (SQLSTATE 45000): {e}")
            
        except pymysql.Error as e:
            # This catches other database errors
            print(f"Database error: {e}")
            
        finally:
            # Cleanup
            try:
                db.execute_non_query("DELETE FROM payment WHERE registration_id = %s", (registration_id,))
                db.execute_non_query("DELETE FROM registration WHERE registration_id = %s", (registration_id,))
                db.execute_non_query("DELETE FROM patient WHERE patient_id = %s", (patient_id,))
            except:
                pass


def main():
    """Run all examples."""
    print("Database Manager Usage Examples")
    print("=" * 50)
    print("\nMake sure to update DB_CONFIG with your credentials!\n")
    
    try:
        example_basic_usage()
        example_context_manager()
        example_insert_update_delete()
        example_stored_procedure()
        example_error_handling()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except pymysql.Error as e:
        print(f"\n✗ Database error: {e}")
        print("\nPlease check:")
        print("  1. Database server is running")
        print("  2. Credentials in DB_CONFIG are correct")
        print("  3. hospital_management database exists and schema is loaded")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == '__main__':
    main()
