"""
Hospital Service Module

This module provides business logic for the hospital management system.
It interacts with the database through the DatabaseManager class from db_util.py.
"""

from typing import List, Dict, Any, Tuple, Optional
from db_util import DatabaseManager, DatabaseError
import pymysql


class HospitalService:
    """
    Business logic service for hospital management system.
    
    This class provides high-level methods for managing hospital operations
    including patient registration, doctor consultations, billing, and inventory.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize HospitalService with a DatabaseManager instance.
        
        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db = db_manager
    
    # ============================================
    # Registration Module
    # ============================================
    
    def get_departments(self) -> List[Dict[str, Any]]:
        """
        Fetch all departments from the database.
        
        Returns:
            List of dictionaries containing department information
            
        Raises:
            pymysql.Error: If database query fails
        """
        return self.db.execute_query("SELECT * FROM department")
    
    def get_doctors_by_dept(self, dept_id: int) -> List[Dict[str, Any]]:
        """
        Fetch doctors based on department ID.
        
        Args:
            dept_id: Department ID to filter doctors
            
        Returns:
            List of dictionaries containing doctor information
            
        Raises:
            pymysql.Error: If database query fails
        """
        return self.db.execute_query(
            "SELECT * FROM doctor WHERE department_id = %s",
            (dept_id,)
        )
    
    def register_patient(self, patient_id: int, dept_id: int, doc_id: int) -> Tuple[int, float]:
        """
        Register a patient by calling the stored procedure sp_submit_registration.
        
        Note: The stored procedure in the database is named 'sp_submit_registration',
        not 'sp_create_registration' as mentioned in some specifications.
        
        Args:
            patient_id: Patient ID
            dept_id: Department ID
            doc_id: Doctor ID
            
        Returns:
            Tuple of (registration_id, pending_payment_amount)
            
        Raises:
            DatabaseError: If database raises custom error
            pymysql.Error: If database operation fails
        """
        try:
            # Call the stored procedure with default payment method
            out_params, result_sets = self.db.call_procedure(
                'sp_submit_registration',
                (patient_id, dept_id, doc_id, None, None)  # None for payment_method and OUT registration_id
            )
            
            # Extract registration_id from OUT parameter
            registration_id = out_params[-1]
            
            # Get the pending payment amount for this registration
            payment_query = """
                SELECT amount FROM payment 
                WHERE registration_id = %s AND payment_type = 'Registration' AND payment_status = 0
            """
            payment_result = self.db.execute_query(payment_query, (registration_id,))
            
            if payment_result:
                pending_amount = float(payment_result[0]['amount'])
            else:
                pending_amount = 0.0
            
            return (registration_id, pending_amount)
            
        except DatabaseError as e:
            # Re-raise custom database errors
            raise DatabaseError(f"Registration failed: {e}")
        except pymysql.Error as e:
            # Re-raise database errors with context
            raise pymysql.Error(f"Database error during registration: {e}")
    
    # ============================================
    # Doctor Module
    # ============================================
    
    def get_waiting_list(self, doctor_id: int) -> List[Dict[str, Any]]:
        """
        Query patients waiting under a specific doctor.
        
        Fetches patients where status is 1 (Awaiting Check/待就诊) and 
        the registration fee has been paid.
        
        Args:
            doctor_id: Doctor ID to filter patients
            
        Returns:
            List of dictionaries containing patient registration information
            
        Raises:
            pymysql.Error: If database query fails
        """
        query = """
            SELECT 
                r.registration_id,
                r.patient_id,
                p.patient_name,
                p.gender,
                p.phone,
                r.registration_date,
                r.registration_time,
                r.chief_complaint,
                r.status
            FROM registration r
            JOIN patient p ON r.patient_id = p.patient_id
            WHERE r.doctor_id = %s 
            AND r.status = 1
            ORDER BY r.registration_date, r.registration_time
        """
        return self.db.execute_query(query, (doctor_id,))
    
    def submit_diagnosis(self, reg_id: int, drug_list: List[Dict[str, Any]]) -> List[int]:
        """
        Submit diagnosis for a patient with a list of prescribed drugs.
        
        Calls the stored procedure sp_finish_consultation for each drug in the list.
        
        Args:
            reg_id: Registration ID
            drug_list: List of dictionaries containing:
                - drug_id: Drug ID
                - quantity: Quantity to prescribe
                - dosage (optional): Dosage instructions, defaults to '按医嘱'
                - duration_days (optional): Duration in days, defaults to 7
                - notes (optional): Additional notes, defaults to ''
                
        Returns:
            List of payment IDs created for each prescription
            
        Raises:
            DatabaseError: If database raises custom error (e.g., insufficient stock)
            pymysql.Error: If database operation fails
        """
        payment_ids = []
        
        try:
            for drug in drug_list:
                drug_id = drug['drug_id']
                quantity = drug['quantity']
                dosage = drug.get('dosage', '按医嘱')
                duration_days = drug.get('duration_days', 7)
                notes = drug.get('notes', '')
                
                # Call the stored procedure for each drug
                out_params, result_sets = self.db.call_procedure(
                    'sp_finish_consultation',
                    (reg_id, drug_id, quantity, dosage, duration_days, notes, None, None)
                )
                
                # Extract payment_id from OUT parameter
                payment_id = out_params[-1]
                payment_ids.append(payment_id)
            
            return payment_ids
            
        except DatabaseError as e:
            # Re-raise custom database errors with context
            raise DatabaseError(f"Diagnosis submission failed: {e}")
        except pymysql.Error as e:
            # Re-raise database errors with context
            raise pymysql.Error(f"Database error during diagnosis submission: {e}")
    
    # ============================================
    # Billing Module
    # ============================================
    
    def get_pending_payments(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all unpaid bills for a specific patient.
        
        Args:
            patient_id: Patient ID
            
        Returns:
            List of dictionaries containing unpaid payment information
            
        Raises:
            pymysql.Error: If database query fails
        """
        query = """
            SELECT 
                p.payment_id,
                p.registration_id,
                p.payment_type,
                p.amount,
                p.payment_method,
                p.payment_status,
                r.registration_date,
                r.doctor_id,
                d.doctor_name
            FROM payment p
            JOIN registration r ON p.registration_id = r.registration_id
            LEFT JOIN doctor d ON r.doctor_id = d.doctor_id
            WHERE r.patient_id = %s AND p.payment_status = 0
            ORDER BY p.created_at
        """
        return self.db.execute_query(query, (patient_id,))
    
    def pay_bill(self, payment_id: int) -> Dict[str, Any]:
        """
        Mark a payment as paid (change payment_status to 1).
        
        This operation may trigger inventory deduction for medicine payments.
        If there is insufficient stock, the error will include specific drug names.
        
        Args:
            payment_id: Payment ID to mark as paid
            
        Returns:
            Dictionary with result information:
                - success: Boolean indicating success
                - message: Success or error message
                - drug_name: (optional) Drug name if inventory shortfall occurred
                
        Raises:
            DatabaseError: If inventory shortfall or other custom database error occurs
            pymysql.Error: If database operation fails
        """
        try:
            # Update payment status to paid
            update_query = """
                UPDATE payment 
                SET payment_status = 1, payment_date = NOW() 
                WHERE payment_id = %s
            """
            affected = self.db.execute_non_query(update_query, (payment_id,))
            
            if affected == 0:
                return {
                    'success': False,
                    'message': f'Payment ID {payment_id} not found or already paid'
                }
            
            return {
                'success': True,
                'message': 'Payment processed successfully'
            }
            
        except DatabaseError as e:
            # Parse the error message to extract drug name for inventory shortfall
            error_msg = str(e)
            drug_name = None
            
            # Check if this is an inventory shortfall error
            if 'Insufficient stock for drug' in error_msg:
                # Extract drug name from error message
                # Error format: "Insufficient stock for drug "DrugName". Required: X, Available: Y"
                try:
                    start = error_msg.index('"') + 1
                    end = error_msg.index('"', start)
                    drug_name = error_msg[start:end]
                except (ValueError, IndexError):
                    drug_name = 'Unknown'
                
                result = {
                    'success': False,
                    'message': error_msg,
                    'drug_name': drug_name,
                    'error_type': 'inventory_shortfall'
                }
                return result
            
            # Other DatabaseError
            raise DatabaseError(f"Payment processing failed: {e}")
            
        except pymysql.Error as e:
            # Re-raise database errors with context
            raise pymysql.Error(f"Database error during payment processing: {e}")
    
    # ============================================
    # Inventory Module
    # ============================================
    
    def get_low_stock_drugs(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch drugs with inventory lower than the specified threshold.
        
        This is useful for pharmacy alerts to restock drugs.
        
        Args:
            threshold: Stock quantity threshold (default: 10)
            
        Returns:
            List of dictionaries containing drug information with low stock
            
        Raises:
            pymysql.Error: If database query fails
        """
        query = """
            SELECT 
                drug_id,
                drug_name,
                drug_code,
                specification,
                unit_price,
                stored_quantity
            FROM drug
            WHERE stored_quantity < %s
            ORDER BY stored_quantity ASC
        """
        return self.db.execute_query(query, (threshold,))
