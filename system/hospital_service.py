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
            raise DatabaseError(f"挂号失败：{e}")
        except pymysql.Error as e:
            # Re-raise database errors with context
            raise pymysql.Error(f"挂号时数据库错误：{e}")
    
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
            raise DatabaseError(f"提交诊断失败：{e}")
        except pymysql.Error as e:
            # Re-raise database errors with context
            raise pymysql.Error(f"提交诊断时数据库错误：{e}")
    
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
                    'message': f'缴费ID {payment_id} 不存在或已支付'
                }
            
            return {
                'success': True,
                'message': '缴费处理成功'
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
            raise DatabaseError(f"缴费处理失败：{e}")
            
        except pymysql.Error as e:
            # Re-raise database errors with context
            raise pymysql.Error(f"缴费时数据库错误：{e}")
    
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
    
    # ============================================
    # Patient Module
    # ============================================
    
    def authenticate_patient(self, id_card: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a patient by their ID card number.
        
        Args:
            id_card: Patient's ID card number
            
        Returns:
            Dictionary containing patient information if found, None otherwise
            
        Raises:
            pymysql.Error: If database query fails
        """
        query = """
            SELECT 
                patient_id,
                patient_name,
                gender,
                date_of_birth,
                phone,
                address,
                id_card
            FROM patient
            WHERE id_card = %s
        """
        result = self.db.execute_query(query, (id_card,))
        return result[0] if result else None
    
    def get_patient_registrations(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all registration records for a specific patient.
        
        Args:
            patient_id: Patient ID
            
        Returns:
            List of dictionaries containing registration information
            
        Raises:
            pymysql.Error: If database query fails
        """
        query = """
            SELECT 
                r.registration_id,
                r.registration_date,
                r.registration_time,
                r.status,
                r.fee,
                r.chief_complaint,
                d.department_name,
                doc.doctor_name,
                CASE 
                    WHEN r.status = 0 THEN '未缴费'
                    WHEN r.status = 1 THEN '待就诊'
                    WHEN r.status = 2 THEN '已完成'
                    ELSE '未知'
                END AS status_text
            FROM registration r
            JOIN department d ON r.department_id = d.department_id
            LEFT JOIN doctor doc ON r.doctor_id = doc.doctor_id
            WHERE r.patient_id = %s
            ORDER BY r.registration_date DESC, r.registration_time DESC
        """
        return self.db.execute_query(query, (patient_id,))
    
    def get_patient_prescriptions(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all prescription records for a specific patient.
        
        Args:
            patient_id: Patient ID
            
        Returns:
            List of dictionaries containing prescription information
            
        Raises:
            pymysql.Error: If database query fails
        """
        query = """
            SELECT 
                p.prescription_id,
                p.registration_id,
                p.quantity,
                p.dosage,
                p.duration_days,
                p.notes,
                p.created_at,
                d.drug_name,
                d.specification,
                d.unit_price,
                (d.unit_price * p.quantity) AS total_cost,
                r.registration_date
            FROM prescription p
            JOIN drug d ON p.drug_id = d.drug_id
            JOIN registration r ON p.registration_id = r.registration_id
            WHERE r.patient_id = %s
            ORDER BY p.created_at DESC
        """
        return self.db.execute_query(query, (patient_id,))
    
    def get_patient_payments(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all payment records for a specific patient.
        
        Args:
            patient_id: Patient ID
            
        Returns:
            List of dictionaries containing payment information
            
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
                p.payment_date,
                p.created_at,
                r.registration_date,
                CASE 
                    WHEN p.payment_status = 0 THEN '未支付'
                    WHEN p.payment_status = 1 THEN '已支付'
                    ELSE '未知'
                END AS payment_status_text
            FROM payment p
            JOIN registration r ON p.registration_id = r.registration_id
            WHERE r.patient_id = %s
            ORDER BY p.created_at DESC
        """
        return self.db.execute_query(query, (patient_id,))
    
    # ============================================
    # Admin Data Maintenance Module
    # ============================================
    
    # ---------- Patient CRUD ----------
    
    def add_patient(self, patient_name: str, gender: str, date_of_birth: str, 
                   phone: str, address: str, id_card: str) -> int:
        """
        Add a new patient to the system.
        
        Args:
            patient_name: Patient name
            gender: Patient gender ('M', 'F', or 'Other')
            date_of_birth: Date of birth (YYYY-MM-DD)
            phone: Phone number
            address: Address
            id_card: ID card number (must be unique)
            
        Returns:
            The newly created patient_id
            
        Raises:
            pymysql.Error: If database operation fails (e.g., duplicate id_card)
        """
        query = """
            INSERT INTO patient (patient_name, gender, date_of_birth, phone, address, id_card)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_non_query(query, (patient_name, gender, date_of_birth, phone, address, id_card))
            # Get the last inserted ID
            result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
            return result[0]['id']
        except pymysql.Error as e:
            raise pymysql.Error(f"添加患者失败：{e}")
    
    def delete_patient(self, patient_id: int) -> Dict[str, Any]:
        """
        Delete a patient with referential integrity checks.
        
        Checks if patient has any registration records before deletion.
        
        Args:
            patient_id: Patient ID to delete
            
        Returns:
            Dictionary with result information:
                - success: Boolean indicating success
                - message: Success or error message
                
        Raises:
            pymysql.Error: If database operation fails
        """
        try:
            # Check if patient has any registrations
            check_query = """
                SELECT COUNT(*) as count FROM registration WHERE patient_id = %s
            """
            result = self.db.execute_query(check_query, (patient_id,))
            
            if result[0]['count'] > 0:
                return {
                    'success': False,
                    'message': f'无法删除该病人，因为该病人有 {result[0]["count"]} 条挂号记录。请先删除相关挂号记录。'
                }
            
            # Attempt to delete
            delete_query = "DELETE FROM patient WHERE patient_id = %s"
            affected = self.db.execute_non_query(delete_query, (patient_id,))
            
            if affected == 0:
                return {
                    'success': False,
                    'message': f'病人ID {patient_id} 不存在'
                }
            
            return {
                'success': True,
                'message': '病人删除成功'
            }
            
        except pymysql.err.IntegrityError as e:
            # Double insurance: catch IntegrityError (1451)
            if e.args[0] == 1451:
                return {
                    'success': False,
                    'message': '无法删除该病人，因为该病人已有关联的挂号或其他记录'
                }
            raise
        except pymysql.Error as e:
            raise pymysql.Error(f"删除患者失败：{e}")
    
    # ---------- Doctor CRUD ----------
    
    def add_doctor(self, doctor_name: str, gender: str, title: str, 
                  department_id: int, phone: str, email: str = None, 
                  specialization: str = None) -> int:
        """
        Add a new doctor to the system with department validation.
        
        Args:
            doctor_name: Doctor name
            gender: Doctor gender ('M', 'F', or 'Other')
            title: Doctor title (e.g., '主任医师', '副主任医师')
            department_id: Department ID (must exist)
            phone: Phone number
            email: Email address (optional)
            specialization: Specialization description (optional)
            
        Returns:
            The newly created doctor_id
            
        Raises:
            DatabaseError: If department doesn't exist
            pymysql.Error: If database operation fails
        """
        # Check if department exists
        dept_check = self.db.execute_query(
            "SELECT department_id FROM department WHERE department_id = %s",
            (department_id,)
        )
        
        if not dept_check:
            raise DatabaseError(f"科室ID {department_id} 不存在，请先添加该科室")
        
        query = """
            INSERT INTO doctor (doctor_name, gender, title, department_id, phone, email, specialization)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_non_query(query, (doctor_name, gender, title, department_id, 
                                             phone, email, specialization))
            result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
            return result[0]['id']
        except pymysql.Error as e:
            raise pymysql.Error(f"添加医生失败：{e}")
    
    def delete_doctor(self, doctor_id: int) -> Dict[str, Any]:
        """
        Delete a doctor with referential integrity checks.
        
        Checks if doctor has any registration records before deletion.
        
        Args:
            doctor_id: Doctor ID to delete
            
        Returns:
            Dictionary with result information:
                - success: Boolean indicating success
                - message: Success or error message
                
        Raises:
            pymysql.Error: If database operation fails
        """
        try:
            # Check if doctor has any registrations
            check_query = """
                SELECT COUNT(*) as count FROM registration WHERE doctor_id = %s
            """
            result = self.db.execute_query(check_query, (doctor_id,))
            
            if result[0]['count'] > 0:
                return {
                    'success': False,
                    'message': f'无法删除该医生，因为该医生有 {result[0]["count"]} 条挂号记录。请先删除相关挂号记录。'
                }
            
            # Attempt to delete
            delete_query = "DELETE FROM doctor WHERE doctor_id = %s"
            affected = self.db.execute_non_query(delete_query, (doctor_id,))
            
            if affected == 0:
                return {
                    'success': False,
                    'message': f'医生ID {doctor_id} 不存在'
                }
            
            return {
                'success': True,
                'message': '医生删除成功'
            }
            
        except pymysql.err.IntegrityError as e:
            # Double insurance: catch IntegrityError (1451)
            if e.args[0] == 1451:
                return {
                    'success': False,
                    'message': '无法删除该医生，因为该医生已有关联的挂号记录'
                }
            raise
        except pymysql.Error as e:
            raise pymysql.Error(f"删除医生失败：{e}")
    
    # ---------- Department CRUD ----------
    
    def add_department(self, department_name: str, description: str = None,
                      location: str = None, phone: str = None) -> int:
        """
        Add a new department to the system.
        
        Args:
            department_name: Department name (must be unique)
            description: Department description (optional)
            location: Department location (optional)
            phone: Department phone (optional)
            
        Returns:
            The newly created department_id
            
        Raises:
            pymysql.Error: If database operation fails (e.g., duplicate name)
        """
        query = """
            INSERT INTO department (department_name, description, location, phone)
            VALUES (%s, %s, %s, %s)
        """
        try:
            self.db.execute_non_query(query, (department_name, description, location, phone))
            result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
            return result[0]['id']
        except pymysql.Error as e:
            raise pymysql.Error(f"添加科室失败：{e}")
    
    def delete_department(self, department_id: int) -> Dict[str, Any]:
        """
        Delete a department with strict referential integrity checks.
        
        Checks if department has any doctors before deletion.
        
        Args:
            department_id: Department ID to delete
            
        Returns:
            Dictionary with result information:
                - success: Boolean indicating success
                - message: Success or error message
                
        Raises:
            pymysql.Error: If database operation fails
        """
        try:
            # Check if department has any doctors
            check_query = """
                SELECT COUNT(*) as count FROM doctor WHERE department_id = %s
            """
            result = self.db.execute_query(check_query, (department_id,))
            
            if result[0]['count'] > 0:
                return {
                    'success': False,
                    'message': f'该科室下仍有 {result[0]["count"]} 位医生，请先转移或删除医生'
                }
            
            # Attempt to delete
            delete_query = "DELETE FROM department WHERE department_id = %s"
            affected = self.db.execute_non_query(delete_query, (department_id,))
            
            if affected == 0:
                return {
                    'success': False,
                    'message': f'科室ID {department_id} 不存在'
                }
            
            return {
                'success': True,
                'message': '科室删除成功'
            }
            
        except pymysql.err.IntegrityError as e:
            # Double insurance: catch IntegrityError (1451)
            if e.args[0] == 1451:
                return {
                    'success': False,
                    'message': '无法删除该科室，因为该科室下仍有医生或其他关联记录'
                }
            raise
        except pymysql.Error as e:
            raise pymysql.Error(f"删除科室失败：{e}")
    
    # ---------- Drug CRUD ----------
    
    def add_drug(self, drug_name: str, drug_code: str, specification: str,
                manufacturer: str, unit_price: float, stored_quantity: int = 0,
                expiry_date: str = None) -> int:
        """
        Add a new drug to the system.
        
        Args:
            drug_name: Drug name
            drug_code: Drug code (must be unique)
            specification: Drug specification (e.g., '500mg', '10ml')
            manufacturer: Manufacturer name
            unit_price: Unit price (must be > 0)
            stored_quantity: Initial stock quantity (default: 0)
            expiry_date: Expiry date (YYYY-MM-DD, optional)
            
        Returns:
            The newly created drug_id
            
        Raises:
            pymysql.Error: If database operation fails (e.g., duplicate drug_code)
        """
        query = """
            INSERT INTO drug (drug_name, drug_code, specification, manufacturer, 
                            unit_price, stored_quantity, expiry_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_non_query(query, (drug_name, drug_code, specification, 
                                             manufacturer, unit_price, stored_quantity, expiry_date))
            result = self.db.execute_query("SELECT LAST_INSERT_ID() as id")
            return result[0]['id']
        except pymysql.Error as e:
            raise pymysql.Error(f"添加药品失败：{e}")
    
    def delete_drug(self, drug_id: int) -> Dict[str, Any]:
        """
        Delete a drug with referential integrity checks.
        
        Checks if drug has any prescription records before deletion.
        
        Args:
            drug_id: Drug ID to delete
            
        Returns:
            Dictionary with result information:
                - success: Boolean indicating success
                - message: Success or error message
                
        Raises:
            pymysql.Error: If database operation fails
        """
        try:
            # Check if drug has any prescriptions
            check_query = """
                SELECT COUNT(*) as count FROM prescription WHERE drug_id = %s
            """
            result = self.db.execute_query(check_query, (drug_id,))
            
            if result[0]['count'] > 0:
                return {
                    'success': False,
                    'message': f'无法删除该药品，因为已有病人的处方包含了此药（{result[0]["count"]} 条处方记录）'
                }
            
            # Attempt to delete
            delete_query = "DELETE FROM drug WHERE drug_id = %s"
            affected = self.db.execute_non_query(delete_query, (drug_id,))
            
            if affected == 0:
                return {
                    'success': False,
                    'message': f'药品ID {drug_id} 不存在'
                }
            
            return {
                'success': True,
                'message': '药品删除成功'
            }
            
        except pymysql.err.IntegrityError as e:
            # Double insurance: catch IntegrityError (1451)
            if e.args[0] == 1451:
                return {
                    'success': False,
                    'message': '无法删除该药品，因为已有病人的处方包含了此药'
                }
            raise
        except pymysql.Error as e:
            raise pymysql.Error(f"删除药品失败：{e}")
    
    # ---------- Get All Methods for Display ----------
    
    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Fetch all patients from the database."""
        query = """
            SELECT patient_id, patient_name, gender, date_of_birth, phone, address, id_card, created_at
            FROM patient
            ORDER BY patient_id DESC
        """
        return self.db.execute_query(query)
    
    def get_all_doctors(self) -> List[Dict[str, Any]]:
        """Fetch all doctors with department information."""
        query = """
            SELECT d.doctor_id, d.doctor_name, d.gender, d.title, d.department_id,
                   dept.department_name, d.phone, d.email, d.specialization, d.created_at
            FROM doctor d
            JOIN department dept ON d.department_id = dept.department_id
            ORDER BY d.doctor_id DESC
        """
        return self.db.execute_query(query)
    
    def get_all_departments(self) -> List[Dict[str, Any]]:
        """Fetch all departments from the database."""
        query = """
            SELECT department_id, department_name, description, location, phone, created_at
            FROM department
            ORDER BY department_id DESC
        """
        return self.db.execute_query(query)
    
    def get_all_drugs(self) -> List[Dict[str, Any]]:
        """Fetch all drugs from the database."""
        query = """
            SELECT drug_id, drug_name, drug_code, specification, manufacturer, 
                   unit_price, stored_quantity, expiry_date, created_at
            FROM drug
            ORDER BY drug_id DESC
        """
        return self.db.execute_query(query)
