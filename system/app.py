"""
Flask Application for Hospital Management System

This application provides web routes for hospital management operations including
patient registration, doctor consultations, billing, and inventory management.
It integrates with the HospitalService class for business logic.
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash
from db_util import DatabaseManager, DatabaseError
from hospital_service import HospitalService
import pymysql
import os

from dotenv import load_dotenv
# 加载环境变量
load_dotenv()  # 默认加载 .env 文件

app = Flask(__name__)
# Use environment variable for secret key, fallback to default for development
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'hospital_management_secret_key_2024')

# Database configuration - use environment variables if available, otherwise fallback to defaults
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'password'),
    'db': os.environ.get('DB_NAME', 'hospital_management')
}

# Initialize database manager and service
db_manager = DatabaseManager(DB_CONFIG)
service = HospitalService(db_manager)


# ============================================
# Route 1: Home and Role Switch
# ============================================
@app.route('/', methods=['GET', 'POST'])
def home():
    """
    Entry point for the system where users can select their roles.
    
    Stores selected role and user_id in session for data filtering.
    """
    if request.method == 'POST':
        role = request.form.get('role')
        user_id = request.form.get('user_id', '')
        
        # Store role and user_id in session
        session['role'] = role
        session['user_id'] = user_id
        
        # Redirect based on role
        if role == 'registrar':
            return redirect(url_for('register'))
        elif role == 'doctor':
            return redirect(url_for('doctor_queue'))
        elif role == 'admin':
            return redirect(url_for('admin_data_management'))
        elif role == 'patient':
            return redirect(url_for('patient_login'))
        else:
            flash('角色选择无效', 'danger')
            return redirect(url_for('home'))
    
    return render_template('home.html')


# ============================================
# Route 2: Registration Module
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Patient registration module.
    
    GET: Show registration form with all departments loaded for selection.
    POST: Accepts Patient ID, Department ID, and Doctor ID to register a patient.
    """
    if request.method == 'GET':
        try:
            # Fetch all departments for the form
            departments = service.get_departments()
            return render_template('register.html', departments=departments)
        except pymysql.Error as e:
            flash(f'加载科室信息出错：{str(e)}', 'danger')
            return render_template('register.html', departments=[])
    
    else:  # POST
        try:
            # Get form data
            patient_id = int(request.form.get('patient_id'))
            dept_id = int(request.form.get('department_id'))
            doc_id = int(request.form.get('doctor_id'))
            
            # Register patient via service
            registration_id, pending_amount = service.register_patient(patient_id, dept_id, doc_id)
            
            # Success message
            flash(f'挂号成功！挂号ID：{registration_id}。待缴费用：¥{pending_amount:.2f}', 'success')
            
            # Redirect to billing/pending payment page
            return redirect(url_for('billing'))
            
        except DatabaseError as e:
            # Capture database-related errors (like "Duplicate Registration")
            flash(str(e), 'danger')
            return redirect(url_for('register'))
        except pymysql.Error as e:
            flash(f'数据库错误：{str(e)}', 'danger')
            return redirect(url_for('register'))
        except ValueError as e:
            flash('输入值无效，请检查您的输入', 'danger')
            return redirect(url_for('register'))


# ============================================
# Route 3: Doctor Queue
# ============================================
@app.route('/doctor/queue', methods=['GET'])
def doctor_queue():
    """
    Displays the queue of patients waiting for consultation under the logged-in doctor.
    
    Filters by doctor_id from session and shows only patients with status=1 (Paid Registration Fee).
    """
    try:
        # Get doctor_id from session
        doctor_id = session.get('user_id')
        
        if not doctor_id:
            flash('请先以医生身份登录', 'warning')
            return redirect(url_for('home'))
        
        # Fetch waiting list for this doctor
        waiting_patients = service.get_waiting_list(int(doctor_id))
        
        return render_template('doctor_queue.html', patients=waiting_patients, doctor_id=doctor_id)
        
    except pymysql.Error as e:
        flash(f'加载患者队列出错：{str(e)}', 'danger')
        return render_template('doctor_queue.html', patients=[], doctor_id=doctor_id)


# ============================================
# Route 4: Diagnosis and Prescription
# ============================================
@app.route('/doctor/diagnose/<int:reg_id>', methods=['GET', 'POST'])
def diagnose(reg_id):
    """
    Diagnosis and prescription page for a specific patient.
    
    GET: Display specific patient info on a diagnosis page.
    POST: Handle dynamic form submission of drug prescriptions.
    """
    if request.method == 'GET':
        try:
            # Fetch patient registration details
            query = """
                SELECT 
                    r.registration_id,
                    r.patient_id,
                    p.patient_name,
                    p.gender,
                    p.date_of_birth,
                    p.phone,
                    r.registration_date,
                    r.registration_time,
                    r.chief_complaint,
                    d.department_name,
                    doc.doctor_name
                FROM registration r
                JOIN patient p ON r.patient_id = p.patient_id
                JOIN department d ON r.department_id = d.department_id
                LEFT JOIN doctor doc ON r.doctor_id = doc.doctor_id
                WHERE r.registration_id = %s
            """
            patient_info = db_manager.execute_query(query, (reg_id,))
            
            if not patient_info:
                flash('未找到挂号记录', 'danger')
                return redirect(url_for('doctor_queue'))
            
            # Fetch available drugs for prescription
            drugs = db_manager.execute_query("SELECT * FROM drug WHERE stored_quantity > 0")
            
            return render_template('diagnose.html', patient=patient_info[0], drugs=drugs, reg_id=reg_id)
            
        except pymysql.Error as e:
            flash(f'加载患者信息出错：{str(e)}', 'danger')
            return redirect(url_for('doctor_queue'))
    
    else:  # POST
        try:
            # Get dynamic form data for drug prescriptions
            # Expected format: drug_id_1, quantity_1, drug_id_2, quantity_2, etc.
            drug_list = []
            
            # Parse form data to extract drug prescriptions
            form_data = request.form
            i = 1
            while f'drug_id_{i}' in form_data:
                drug_id = form_data.get(f'drug_id_{i}')
                quantity = form_data.get(f'quantity_{i}')
                dosage = form_data.get(f'dosage_{i}', '按医嘱')
                duration_days = form_data.get(f'duration_days_{i}', '7')
                notes = form_data.get(f'notes_{i}', '')
                
                if drug_id and quantity:
                    drug_list.append({
                        'drug_id': int(drug_id),
                        'quantity': int(quantity),
                        'dosage': dosage,
                        'duration_days': int(duration_days),
                        'notes': notes
                    })
                i += 1
            
            if not drug_list:
                flash('未提供处方', 'warning')
                return redirect(url_for('diagnose', reg_id=reg_id))
            
            # Submit diagnosis with prescriptions
            payment_ids = service.submit_diagnosis(reg_id, drug_list)
            
            flash(f'诊断提交成功！缴费ID：{", ".join(map(str, payment_ids))}', 'success')
            return redirect(url_for('doctor_queue'))
            
        except DatabaseError as e:
            # Capture inventory errors (like "XX drug out of stock")
            flash(str(e), 'danger')
            return redirect(url_for('diagnose', reg_id=reg_id))
        except pymysql.Error as e:
            flash(f'数据库错误：{str(e)}', 'danger')
            return redirect(url_for('diagnose', reg_id=reg_id))
        except ValueError as e:
            flash('处方输入值无效', 'danger')
            return redirect(url_for('diagnose', reg_id=reg_id))


# ============================================
# Route 5: Billing Center
# ============================================
@app.route('/billing', methods=['GET', 'POST'])
def billing():
    """
    Billing center for viewing and processing payments.
    
    GET: Shows unpaid bills for a patient ID.
    POST: Process payment confirmation.
    """
    if request.method == 'GET':
        # Get patient_id from query parameter
        patient_id = request.args.get('patient_id', '')
        
        if patient_id:
            try:
                # Fetch pending payments for this patient
                pending_payments = service.get_pending_payments(int(patient_id))
                return render_template('billing.html', payments=pending_payments, patient_id=patient_id)
            except pymysql.Error as e:
                flash(f'加载缴费信息出错：{str(e)}', 'danger')
                return render_template('billing.html', payments=[], patient_id=patient_id)
        else:
            # Show form to enter patient ID
            return render_template('billing.html', payments=[], patient_id='')
    
    else:  # POST
        try:
            # Get payment_id from form
            payment_id = int(request.form.get('payment_id'))
            
            # Process payment
            result = service.pay_bill(payment_id)
            
            if result['success']:
                flash(result['message'], 'success')
            else:
                flash(result['message'], 'danger')
            
            # Redirect back to billing page
            patient_id = request.form.get('patient_id', '')
            return redirect(url_for('billing', patient_id=patient_id))
            
        except DatabaseError as e:
            # Capture errors like "Insufficient Inventory"
            flash(str(e), 'danger')
            patient_id = request.form.get('patient_id', '')
            return redirect(url_for('billing', patient_id=patient_id))
        except pymysql.Error as e:
            flash(f'数据库错误：{str(e)}', 'danger')
            patient_id = request.form.get('patient_id', '')
            return redirect(url_for('billing', patient_id=patient_id))
        except ValueError as e:
            flash('缴费ID无效', 'danger')
            patient_id = request.form.get('patient_id', '')
            return redirect(url_for('billing', patient_id=patient_id))


# ============================================
# Route 6: Inventory and Pharmacy Management
# ============================================
@app.route('/admin/inventory', methods=['GET'])
def admin_inventory():
    """
    Admin inventory management page.
    
    Enables real-time monitoring of drug inventory with configurable threshold.
    """
    try:
        # Get threshold from query parameter (default=10)
        threshold = request.args.get('threshold', 10, type=int)
        
        # Fetch drugs below stock threshold
        low_stock_drugs = service.get_low_stock_drugs(threshold)
        
        return render_template('admin_inventory.html', drugs=low_stock_drugs, threshold=threshold)
        
    except pymysql.Error as e:
        flash(f'加载库存信息出错：{str(e)}', 'danger')
        return render_template('admin_inventory.html', drugs=[], threshold=10)


# ============================================
# Additional Helper Routes
# ============================================
@app.route('/api/doctors/<int:dept_id>', methods=['GET'])
def get_doctors_by_department(dept_id):
    """
    API endpoint to get doctors by department ID.
    Used for dynamic form updates on the registration page.
    """
    try:
        doctors = service.get_doctors_by_dept(dept_id)
        return {'success': True, 'doctors': doctors}
    except pymysql.Error as e:
        return {'success': False, 'error': str(e)}, 500


@app.route('/logout')
def logout():
    """Clear session and redirect to home."""
    session.clear()
    flash('已成功退出登录', 'success')
    return redirect(url_for('home'))


# ============================================
# Route 7: Patient Login
# ============================================
@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    """
    Patient login module using ID card number.
    
    GET: Show login form for ID card entry.
    POST: Authenticate patient by ID card and redirect to portal.
    """
    if request.method == 'GET':
        return render_template('patient_login.html')
    
    else:  # POST
        try:
            # Get ID card from form
            id_card = request.form.get('id_card', '').strip()
            
            if not id_card:
                flash('请输入您的身份证号', 'warning')
                return redirect(url_for('patient_login'))
            
            # Authenticate patient
            patient = service.authenticate_patient(id_card)
            
            if patient:
                # Store patient info in session
                session['role'] = 'patient'
                session['patient_id'] = patient['patient_id']
                session['patient_name'] = patient['patient_name']
                
                flash(f'欢迎，{patient["patient_name"]}！', 'success')
                return redirect(url_for('patient_portal'))
            else:
                flash('身份证号无效，未找到患者信息', 'danger')
                return redirect(url_for('patient_login'))
                
        except pymysql.Error as e:
            # Log the error server-side for debugging
            app.logger.error(f'Database error during patient login: {str(e)}')
            flash('处理您的请求时发生错误，请稍后再试', 'danger')
            return redirect(url_for('patient_login'))


# ============================================
# Route 8: Patient Portal
# ============================================
@app.route('/patient/portal', methods=['GET'])
def patient_portal():
    """
    Patient personal center displaying registration, prescription, and payment history.
    
    GET: Show all patient records including registrations, prescriptions, and payments.
    """
    try:
        # Check if patient is logged in
        patient_id = session.get('patient_id')
        
        if not patient_id:
            flash('请先登录', 'warning')
            return redirect(url_for('patient_login'))
        
        # Fetch patient records
        registrations = service.get_patient_registrations(patient_id)
        prescriptions = service.get_patient_prescriptions(patient_id)
        payments = service.get_patient_payments(patient_id)
        
        return render_template(
            'patient_portal.html',
            patient_name=session.get('patient_name'),
            registrations=registrations,
            prescriptions=prescriptions,
            payments=payments
        )
        
    except pymysql.Error as e:
        # Log the error server-side for debugging
        app.logger.error(f'Error loading patient records: {str(e)}')
        flash('加载记录时发生错误，请稍后再试', 'danger')
        return render_template(
            'patient_portal.html',
            patient_name=session.get('patient_name'),
            registrations=[],
            prescriptions=[],
            payments=[]
        )


# ============================================
# Route 9: Admin Data Management
# ============================================
@app.route('/admin/data', methods=['GET', 'POST'])
def admin_data_management():
    """
    Admin data management page with tabs for Patient, Doctor, Department, and Drug.
    
    GET: Display all entities with forms to add new records.
    POST: Handle adding or deleting records.
    """
    if request.method == 'GET':
        try:
            # Fetch all data for display
            patients = service.get_all_patients()
            doctors = service.get_all_doctors()
            departments = service.get_all_departments()
            drugs = service.get_all_drugs()
            
            return render_template('admin_data_management.html',
                                 patients=patients,
                                 doctors=doctors,
                                 departments=departments,
                                 drugs=drugs)
        except pymysql.Error as e:
            flash(f'加载数据出错：{str(e)}', 'danger')
            return render_template('admin_data_management.html',
                                 patients=[], doctors=[], departments=[], drugs=[])
    
    else:  # POST
        action = request.form.get('action')
        entity_type = request.form.get('entity_type')
        
        try:
            # Handle ADD operations
            if action == 'add':
                if entity_type == 'patient':
                    patient_name = request.form.get('patient_name')
                    gender = request.form.get('gender')
                    date_of_birth = request.form.get('date_of_birth')
                    phone = request.form.get('phone')
                    address = request.form.get('address', '')
                    id_card = request.form.get('id_card')
                    
                    patient_id = service.add_patient(patient_name, gender, date_of_birth, 
                                                    phone, address, id_card)
                    flash(f'病人添加成功！病人ID: {patient_id}', 'success')
                
                elif entity_type == 'doctor':
                    doctor_name = request.form.get('doctor_name')
                    gender = request.form.get('gender')
                    title = request.form.get('title')
                    department_id = int(request.form.get('department_id'))
                    phone = request.form.get('phone')
                    email = request.form.get('email', None)
                    specialization = request.form.get('specialization', None)
                    
                    doctor_id = service.add_doctor(doctor_name, gender, title, department_id,
                                                   phone, email, specialization)
                    flash(f'医生添加成功！医生ID: {doctor_id}', 'success')
                
                elif entity_type == 'department':
                    department_name = request.form.get('department_name')
                    description = request.form.get('description', None)
                    location = request.form.get('location', None)
                    phone = request.form.get('phone', None)
                    
                    dept_id = service.add_department(department_name, description, location, phone)
                    flash(f'科室添加成功！科室ID: {dept_id}', 'success')
                
                elif entity_type == 'drug':
                    drug_name = request.form.get('drug_name')
                    drug_code = request.form.get('drug_code')
                    specification = request.form.get('specification')
                    manufacturer = request.form.get('manufacturer')
                    unit_price = float(request.form.get('unit_price'))
                    stored_quantity = int(request.form.get('stored_quantity', 0))
                    expiry_date = request.form.get('expiry_date', None)
                    if expiry_date == '':
                        expiry_date = None
                    
                    drug_id = service.add_drug(drug_name, drug_code, specification, manufacturer,
                                              unit_price, stored_quantity, expiry_date)
                    flash(f'药品添加成功！药品ID: {drug_id}', 'success')
            
            # Handle DELETE operations
            elif action == 'delete':
                if entity_type == 'patient':
                    patient_id = int(request.form.get('id'))
                    result = service.delete_patient(patient_id)
                    if result['success']:
                        flash(result['message'], 'success')
                    else:
                        flash(result['message'], 'danger')
                
                elif entity_type == 'doctor':
                    doctor_id = int(request.form.get('id'))
                    result = service.delete_doctor(doctor_id)
                    if result['success']:
                        flash(result['message'], 'success')
                    else:
                        flash(result['message'], 'danger')
                
                elif entity_type == 'department':
                    department_id = int(request.form.get('id'))
                    result = service.delete_department(department_id)
                    if result['success']:
                        flash(result['message'], 'success')
                    else:
                        flash(result['message'], 'danger')
                
                elif entity_type == 'drug':
                    drug_id = int(request.form.get('id'))
                    result = service.delete_drug(drug_id)
                    if result['success']:
                        flash(result['message'], 'success')
                    else:
                        flash(result['message'], 'danger')
            
            return redirect(url_for('admin_data_management'))
            
        except DatabaseError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin_data_management'))
        except pymysql.Error as e:
            flash(f'数据库错误: {str(e)}', 'danger')
            return redirect(url_for('admin_data_management'))
        except ValueError as e:
            flash('输入值无效，请检查您的输入', 'danger')
            return redirect(url_for('admin_data_management'))


# ============================================
# Error Handlers
# ============================================
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    flash('页面未找到', 'danger')
    return redirect(url_for('home'))


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    flash('发生内部错误', 'danger')
    return redirect(url_for('home'))


# ============================================
# Application Entry Point
# ============================================
if __name__ == '__main__':
    # Use environment variable for debug mode, default to False for security
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
