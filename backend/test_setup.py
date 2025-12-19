"""
Demo Script for Hospital Management System Flask App

This script demonstrates how to use the HospitalService class
and verifies the database connection before running the Flask app.
"""

from db_util import DatabaseManager, DatabaseError
from hospital_service import HospitalService
import pymysql

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'db': 'hospital_management'
}

def test_database_connection():
    """Test if database connection works."""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        db = DatabaseManager(DB_CONFIG)
        print("✓ Database connection successful!")
        
        # Test a simple query
        result = db.execute_query("SELECT 1 as test")
        if result:
            print("✓ Query execution successful!")
        
        db.close()
        return True
    except pymysql.Error as e:
        print(f"✗ Database connection failed: {e}")
        print("\nPlease check:")
        print("  1. MySQL server is running")
        print("  2. Database credentials in DB_CONFIG are correct")
        print("  3. Database 'hospital_management' exists")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_hospital_service():
    """Test HospitalService functionality."""
    print("\n" + "=" * 60)
    print("Testing HospitalService")
    print("=" * 60)
    
    try:
        db = DatabaseManager(DB_CONFIG)
        service = HospitalService(db)
        
        # Test get_departments
        print("\n1. Testing get_departments()...")
        departments = service.get_departments()
        print(f"   ✓ Found {len(departments)} departments")
        if departments:
            print(f"   Sample: {departments[0]['department_name']}")
        
        # Test get_low_stock_drugs
        print("\n2. Testing get_low_stock_drugs()...")
        low_stock = service.get_low_stock_drugs(threshold=100)
        print(f"   ✓ Found {len(low_stock)} drugs below threshold")
        
        db.close()
        print("\n✓ All HospitalService tests passed!")
        return True
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def print_available_routes():
    """Print all available Flask routes."""
    print("\n" + "=" * 60)
    print("Available Flask Routes")
    print("=" * 60)
    
    routes = [
        ("Home/Role Selection", "GET/POST", "/"),
        ("Patient Registration", "GET/POST", "/register"),
        ("Doctor Queue", "GET", "/doctor/queue"),
        ("Diagnosis & Prescription", "GET/POST", "/doctor/diagnose/<reg_id>"),
        ("Billing Center", "GET/POST", "/billing"),
        ("Admin Inventory", "GET", "/admin/inventory"),
        ("Get Doctors by Dept (API)", "GET", "/api/doctors/<dept_id>"),
        ("Logout", "GET", "/logout"),
    ]
    
    for name, methods, path in routes:
        print(f"  • {name:30s} {methods:10s} {path}")


def main():
    """Run all tests."""
    print("\nHospital Management System - Pre-Flight Check")
    print("=" * 60)
    
    # Test database connection
    db_ok = test_database_connection()
    
    if not db_ok:
        print("\n⚠️  Cannot proceed without database connection.")
        print("Please fix the database configuration and try again.")
        return
    
    # Test service
    service_ok = test_hospital_service()
    
    if not service_ok:
        print("\n⚠️  HospitalService tests failed.")
        return
    
    # Print routes
    print_available_routes()
    
    print("\n" + "=" * 60)
    print("✓ All checks passed! Ready to run Flask application.")
    print("=" * 60)
    print("\nTo start the Flask application, run:")
    print("  python3 app.py")
    print("\nThen open your browser to:")
    print("  http://localhost:5000")
    print()


if __name__ == '__main__':
    main()
