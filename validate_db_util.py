"""
Validation script for db_util.py module.
This script validates the structure and implementation without requiring pymysql.
"""

import ast
import re


def validate_module_structure():
    """Validate the structure of db_util.py"""
    print("=" * 60)
    print("Database Utility Module Validation")
    print("=" * 60)
    
    with open('db_util.py', 'r') as f:
        content = f.read()
        tree = ast.parse(content)
    
    results = []
    
    # Check 1: Module docstring
    print("\n1. Checking module docstring...")
    module_docstring = ast.get_docstring(tree)
    if module_docstring:
        print("   ✓ Module has docstring")
        results.append(True)
    else:
        print("   ✗ Module missing docstring")
        results.append(False)
    
    # Check 2: Required imports
    print("\n2. Checking imports...")
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend([alias.name for alias in node.names])
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    
    required_imports = ['pymysql', 'typing']
    missing_imports = [imp for imp in required_imports if imp not in imports]
    
    if not missing_imports:
        print(f"   ✓ All required imports present: {required_imports}")
        results.append(True)
    else:
        print(f"   ✗ Missing imports: {missing_imports}")
        results.append(False)
    
    # Check 3: DatabaseError exception class
    print("\n3. Checking DatabaseError exception...")
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    db_error = next((cls for cls in classes if cls.name == 'DatabaseError'), None)
    
    if db_error:
        # Check inheritance
        if db_error.bases and any(hasattr(base, 'id') and base.id == 'Exception' for base in db_error.bases):
            print("   ✓ DatabaseError inherits from Exception")
            results.append(True)
        else:
            print("   ✗ DatabaseError does not inherit from Exception")
            results.append(False)
    else:
        print("   ✗ DatabaseError class not found")
        results.append(False)
    
    # Check 4: DatabaseManager class
    print("\n4. Checking DatabaseManager class...")
    db_manager = next((cls for cls in classes if cls.name == 'DatabaseManager'), None)
    
    if db_manager:
        print("   ✓ DatabaseManager class found")
        results.append(True)
        
        # Check methods
        print("\n5. Checking DatabaseManager methods...")
        methods = [node.name for node in db_manager.body if isinstance(node, ast.FunctionDef)]
        
        required_methods = {
            '__init__': 'Initialize with database config',
            'execute_query': 'Execute SELECT statements',
            'execute_non_query': 'Execute INSERT/UPDATE/DELETE',
            'call_procedure': 'Call stored procedures',
            '_handle_database_error': 'Handle SQLSTATE 45000',
            'close': 'Close connection',
            '__enter__': 'Context manager enter',
            '__exit__': 'Context manager exit'
        }
        
        all_present = True
        for method, description in required_methods.items():
            if method in methods:
                print(f"   ✓ {method}: {description}")
            else:
                print(f"   ✗ {method}: {description} - MISSING")
                all_present = False
        
        results.append(all_present)
        
        # Check method signatures
        print("\n6. Checking method signatures...")
        method_nodes = [node for node in db_manager.body if isinstance(node, ast.FunctionDef)]
        
        # Check __init__ signature
        init_method = next((m for m in method_nodes if m.name == '__init__'), None)
        if init_method:
            args = [arg.arg for arg in init_method.args.args]
            if 'self' in args and 'config' in args:
                print("   ✓ __init__(self, config) - correct signature")
                results.append(True)
            else:
                print(f"   ✗ __init__ signature incorrect: {args}")
                results.append(False)
        
        # Check execute_query signature
        execute_query = next((m for m in method_nodes if m.name == 'execute_query'), None)
        if execute_query:
            args = [arg.arg for arg in execute_query.args.args]
            if 'self' in args and 'sql' in args and 'params' in args:
                print("   ✓ execute_query(self, sql, params) - correct signature")
                results.append(True)
            else:
                print(f"   ✗ execute_query signature incorrect: {args}")
                results.append(False)
        
        # Check execute_non_query signature
        execute_non_query = next((m for m in method_nodes if m.name == 'execute_non_query'), None)
        if execute_non_query:
            args = [arg.arg for arg in execute_non_query.args.args]
            if 'self' in args and 'sql' in args and 'params' in args:
                print("   ✓ execute_non_query(self, sql, params) - correct signature")
                results.append(True)
            else:
                print(f"   ✗ execute_non_query signature incorrect: {args}")
                results.append(False)
        
        # Check call_procedure signature
        call_procedure = next((m for m in method_nodes if m.name == 'call_procedure'), None)
        if call_procedure:
            args = [arg.arg for arg in call_procedure.args.args]
            if 'self' in args and 'proc_name' in args and 'params' in args:
                print("   ✓ call_procedure(self, proc_name, params) - correct signature")
                results.append(True)
            else:
                print(f"   ✗ call_procedure signature incorrect: {args}")
                results.append(False)
    else:
        print("   ✗ DatabaseManager class not found")
        results.append(False)
    
    # Check 7: Docstrings for all methods
    print("\n7. Checking method docstrings...")
    if db_manager:
        method_nodes = [node for node in db_manager.body if isinstance(node, ast.FunctionDef)]
        all_documented = True
        for method in method_nodes:
            if ast.get_docstring(method):
                print(f"   ✓ {method.name} has docstring")
            else:
                print(f"   ✗ {method.name} missing docstring")
                all_documented = False
        results.append(all_documented)
    
    # Check 8: Implementation details
    print("\n8. Checking implementation details...")
    
    # Check for pymysql.connect usage
    if 'pymysql.connect' in content:
        print("   ✓ Uses pymysql.connect")
        results.append(True)
    else:
        print("   ✗ Missing pymysql.connect")
        results.append(False)
    
    # Check for cursor.callproc usage
    if 'callproc' in content:
        print("   ✓ Uses cursor.callproc for stored procedures")
        results.append(True)
    else:
        print("   ✗ Missing cursor.callproc")
        results.append(False)
    
    # Check for commit/rollback
    if 'commit' in content and 'rollback' in content:
        print("   ✓ Implements commit and rollback")
        results.append(True)
    else:
        print("   ✗ Missing commit or rollback")
        results.append(False)
    
    # Check for SQLSTATE 45000 handling
    if '45000' in content or '1001' in content or '1002' in content:
        print("   ✓ Handles SQLSTATE 45000 errors")
        results.append(True)
    else:
        print("   ✗ Missing SQLSTATE 45000 handling")
        results.append(False)
    
    # Check for DictCursor
    if 'DictCursor' in content:
        print("   ✓ Uses DictCursor for dictionary results")
        results.append(True)
    else:
        print("   ✗ Missing DictCursor")
        results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ All validation checks passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} validation check(s) failed")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(validate_module_structure())
