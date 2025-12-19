# Database Utility Module (db_util.py)

A Python database utility module for streamlined MySQL database operations using the `pymysql` library.

## Features

- **Easy Connection Management**: Simple initialization with configuration dictionary
- **Query Execution**: Execute SELECT queries with automatic result formatting
- **Non-Query Operations**: Handle INSERT, UPDATE, DELETE with automatic commit/rollback
- **Stored Procedures**: Execute stored procedures with OUT parameter support
- **Custom Exception Handling**: Automatic parsing of SQLSTATE 45000 errors into Python exceptions
- **Context Manager Support**: Use with `with` statement for automatic resource cleanup
- **Transaction Safety**: Automatic rollback on errors

## Installation

### Prerequisites

```bash
pip install pymysql
```

### Files

- `db_util.py` - Main database utility module
- `test_db_util.py` - Comprehensive test suite
- `example_usage.py` - Usage examples and demonstrations

## Usage

### Basic Usage

```python
from backend.db_util import DatabaseManager, DatabaseError

# Configure database connection
config = {
   'host': 'localhost',
   'user': 'your_username',
   'password': 'your_password',
   'db': 'hospital_management'
}

# Create database manager
db = DatabaseManager(config)

# Execute a query
results = db.execute_query("SELECT * FROM department")
for row in results:
   print(row)

# Close connection
db.close()
```

### Using Context Manager

```python
with DatabaseManager(config) as db:
    results = db.execute_query("SELECT * FROM patient LIMIT 5")
    # Connection automatically closed when exiting the with block
```

### Execute Non-Query (INSERT/UPDATE/DELETE)

```python
with DatabaseManager(config) as db:
    # INSERT
    affected = db.execute_non_query(
        """INSERT INTO patient (patient_name, gender, date_of_birth, phone, address, id_card)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        ('John Doe', 'M', '1990-01-01', '1234567890', 'Address', 'ID123')
    )
    
    # UPDATE
    affected = db.execute_non_query(
        "UPDATE patient SET address = %s WHERE id_card = %s",
        ('New Address', 'ID123')
    )
    
    # DELETE
    affected = db.execute_non_query(
        "DELETE FROM patient WHERE id_card = %s",
        ('ID123',)
    )
```

### Call Stored Procedures

```python
with DatabaseManager(config) as db:
    # Call procedure with OUT parameters
    out_params, result_sets = db.call_procedure(
        'sp_add_patient',
        ('Jane Smith', 'F', '1985-05-15', '9876543210', 'Address', 'ID456', None)
    )
    
    # Access OUT parameter (last parameter)
    patient_id = out_params[-1]
    print(f"Patient ID: {patient_id}")
    
    # Access result sets if procedure returns them
    if result_sets:
        for result_set in result_sets:
            for row in result_set:
                print(row)
```

### Error Handling

```python
from backend.db_util import DatabaseManager, DatabaseError
import pymysql

with DatabaseManager(config) as db:
   try:
      # This might trigger a database error
      db.execute_non_query("INSERT INTO patient ...")

   except DatabaseError as e:
      # Custom exception for SQLSTATE 45000 errors
      # These are user-defined errors from stored procedures/triggers
      print(f"Business logic error: {e}")

   except pymysql.Error as e:
      # Other database errors
      print(f"Database error: {e}")
```

## API Reference

### DatabaseManager Class

#### `__init__(config: Dict[str, Any])`

Initialize database connection.

**Parameters:**
- `config`: Dictionary with keys: `host`, `user`, `password`, `db`

**Raises:**
- `pymysql.Error`: If connection fails

#### `execute_query(sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]`

Execute SELECT query and return results as list of dictionaries.

**Parameters:**
- `sql`: SQL SELECT statement
- `params`: Optional tuple of query parameters

**Returns:**
- List of dictionaries (each dict represents a row)

**Raises:**
- `DatabaseError`: If SQLSTATE 45000 error occurs
- `pymysql.Error`: For other database errors

#### `execute_non_query(sql: str, params: Optional[Tuple] = None) -> int`

Execute INSERT, UPDATE, or DELETE statement.

**Parameters:**
- `sql`: SQL statement (INSERT/UPDATE/DELETE)
- `params`: Optional tuple of query parameters

**Returns:**
- Number of affected rows

**Raises:**
- `DatabaseError`: If SQLSTATE 45000 error occurs
- `pymysql.Error`: For other database errors

#### `call_procedure(proc_name: str, params: Optional[Tuple] = None) -> Tuple[Any, List[Dict[str, Any]]]`

Execute stored procedure.

**Parameters:**
- `proc_name`: Name of stored procedure
- `params`: Optional tuple of parameters (IN and OUT)

**Returns:**
- Tuple of (OUT parameters, list of result sets)

**Raises:**
- `DatabaseError`: If SQLSTATE 45000 error occurs
- `pymysql.Error`: For other database errors

#### `close() -> None`

Close the database connection.

### DatabaseError Exception

Custom exception class for database errors with SQLSTATE 45000. These are user-defined errors raised by stored procedures or triggers in the database.

## Examples

Run the example script:

```bash
python example_usage.py
```

Make sure to update the `DB_CONFIG` in `example_usage.py` with your database credentials.

## SQLSTATE 45000 Error Handling

This module has special handling for SQLSTATE 45000 errors, which are user-defined errors in MySQL. When a stored procedure or trigger raises an error with SQLSTATE 45000, it is automatically caught and raised as a `DatabaseError` exception with the original error message.

Example from hospital management system:

```python
try:
    # Try to create prescription with insufficient stock
    db.call_procedure('sp_create_prescription', (..., quantity=999999, ...))
except DatabaseError as e:
    # Will catch: "Insufficient stock for drug..."
    print(f"Stock error: {e}")
```

## Transaction Management

- `execute_non_query`: Automatically commits on success, rolls back on error
- `call_procedure`: Automatically commits on success, rolls back on error
- `execute_query`: No transaction management (read-only)

## Best Practices

1. **Use context manager**: Ensures connections are properly closed
   ```python
   with DatabaseManager(config) as db:
       # Your code here
   ```

2. **Use parameterized queries**: Prevents SQL injection
   ```python
   db.execute_query("SELECT * FROM patient WHERE id = %s", (patient_id,))
   ```

3. **Handle exceptions appropriately**: Distinguish between business logic errors (DatabaseError) and other errors
   ```python
   try:
       db.execute_non_query(...)
   except DatabaseError as e:
       # Handle business logic error
   except pymysql.Error as e:
       # Handle database error
   ```

4. **Close connections**: Always close or use context manager
   ```python
   db = DatabaseManager(config)
   try:
       # Your code
   finally:
       db.close()
   ```

## License

This module is part of the Hospital Management System project. See LICENSE file for details.
