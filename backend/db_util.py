"""
Database Utility Module for Hospital Management System

This module provides a DatabaseManager class that streamlines database operations
using the pymysql library. It handles connections, queries, and stored procedures
with proper error handling and custom exceptions.
"""

import pymysql
from typing import Dict, List, Tuple, Any, Optional


class DatabaseError(Exception):
    """Custom exception for database errors with SQLSTATE 45000."""
    pass


class DatabaseManager:
    """
    Database Manager class for handling MySQL database operations.
    
    This class provides methods for executing queries, non-queries, and stored
    procedures with proper connection management and error handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the DatabaseManager with database connection.
        
        Args:
            config: Dictionary containing database connection parameters:
                   - host: Database host address
                   - user: Database username
                   - password: Database password
                   - db: Database name
        
        Raises:
            pymysql.Error: If connection to database fails
        """
        try:
            self.connection = pymysql.connect(
                host=config['host'],
                user=config['user'],
                password=config['password'],
                db=config['db'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
        except pymysql.Error as e:
            raise pymysql.Error(f"Failed to connect to database: {e}") from e
    
    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL SELECT query and return results as a list of dictionaries.
        
        Args:
            sql: SQL SELECT statement to execute
            params: Optional tuple of parameters for parameterized query
        
        Returns:
            List of dictionaries where each dictionary represents a row
        
        Raises:
            pymysql.Error: If query execution fails
            DatabaseError: If database raises SQLSTATE 45000 error
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return results
        except pymysql.Error as e:
            self._handle_database_error(e)
    
    def execute_non_query(self, sql: str, params: Optional[Tuple] = None) -> int:
        """
        Execute a non-SELECT SQL statement (INSERT, UPDATE, DELETE).
        
        This method commits changes to the database automatically.
        
        Args:
            sql: SQL statement to execute (INSERT, UPDATE, DELETE)
            params: Optional tuple of parameters for parameterized query
        
        Returns:
            Number of rows affected by the query
        
        Raises:
            pymysql.Error: If query execution fails
            DatabaseError: If database raises SQLSTATE 45000 error
        """
        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                self.connection.commit()
                return affected_rows
        except pymysql.Error as e:
            self.connection.rollback()
            self._handle_database_error(e)

    def call_procedure(self, proc_name: str, params: Optional[Tuple] = None) -> Tuple[Any, List[Dict[str, Any]]]:
        try:
            with self.connection.cursor() as cursor:
                # 1. 执行存储过程
                # 这一步会创建名为 @_proc_name_0, @_proc_name_1... 的 MySQL 变量
                cursor.callproc(proc_name, params or ())

                # 2. 【关键修复】获取更新后的 OUT 参数
                # 我们需要查询 MySQL 内部的会话变量
                updated_params = params
                if params:
                    # 构建查询语句，例如: SELECT @_sp_add_patient_0, @_sp_add_patient_1...
                    param_vars = [f"@_{proc_name}_{i}" for i in range(len(params))]
                    cursor.execute(f"SELECT {', '.join(param_vars)}")
                    # fetchone() 会返回一个包含所有变量最新值的 tuple 或 dict
                    result = cursor.fetchone()
                    if isinstance(result, dict):
                        updated_params = tuple(result.values())
                    else:
                        updated_params = result

                # 3. 获取结果集 (Result Sets)
                result_sets = []
                # 获取第一个结果集
                try:
                    results = cursor.fetchall()
                    if results:
                        result_sets.append(results)
                except:
                    pass

                # 获取后续可能存在的多个结果集
                while cursor.nextset():
                    try:
                        results = cursor.fetchall()
                        if results:
                            result_sets.append(results)
                    except:
                        pass

                self.connection.commit()

                # 返回更新后的参数和结果集
                return updated_params, result_sets

        except pymysql.Error as e:
            self.connection.rollback()
            # self._handle_database_error(e) # 确保你有这个处理函数
            raise e

    def _handle_database_error(self, error: pymysql.Error) -> None:
        """
        Handle database errors and convert SQLSTATE 45000 to custom exception.
        
        This method intercepts database errors with SQLSTATE 45000 (user-defined
        exceptions from triggers or stored procedures) and raises them as
        DatabaseError with the original message.
        
        Args:
            error: The pymysql.Error exception to handle
        
        Raises:
            DatabaseError: If error has SQLSTATE 45000
            pymysql.Error: For all other database errors
        """
        # Check if error has SQLSTATE 45000 (user-defined exception)
        if hasattr(error, 'args') and len(error.args) >= 2:
            error_code = error.args[0]
            error_message = str(error.args[1]) if len(error.args) > 1 else str(error)
            
            # SQLSTATE 45000 is used for user-defined errors in MySQL
            # The error code in pymysql will be a custom MYSQL_ERRNO set in the SIGNAL statement
            # We need to parse the error message to detect if it's from SQLSTATE 45000
            
            # Check if this is a SQLSTATE 45000 error by examining the error message
            # or by checking known error codes set in stored procedures (1001-1004 in our case)
            if error_code in (1001, 1002, 1003, 1004):
                # These are our custom error codes from stored procedures/triggers
                raise DatabaseError(error_message)
        
        # For all other errors, re-raise as pymysql.Error
        raise error
    
    def close(self) -> None:
        """
        Close the database connection.
        
        This method should be called when the DatabaseManager is no longer needed
        to free up database resources.
        """
        if self.connection:
            self.connection.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
