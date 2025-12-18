-- ============================================
-- Hospital Management System Database Design
-- ============================================
-- This script creates a normalized database schema for a hospital management system
-- with proper constraints, stored procedures, and triggers.

-- Drop existing objects if they exist (for clean re-execution)
DROP TRIGGER IF EXISTS trig_reduce_stock;
DROP TRIGGER IF EXISTS trig_update_reg_status;
DROP PROCEDURE IF EXISTS sp_create_registration;
DROP TABLE IF EXISTS prescription;
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS registration;
DROP TABLE IF EXISTS doctor;
DROP TABLE IF EXISTS drug;
DROP TABLE IF EXISTS department;
DROP TABLE IF EXISTS patient;

-- ============================================
-- Table: patient
-- Stores patient information
-- ============================================
CREATE TABLE patient (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_name VARCHAR(100) NOT NULL,
    gender ENUM('M', 'F', 'Other') NOT NULL,
    date_of_birth DATE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address VARCHAR(255),
    id_card VARCHAR(20) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Patient information table';

-- ============================================
-- Table: department
-- Stores hospital departments
-- ============================================
CREATE TABLE department (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    location VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Department information table';

-- ============================================
-- Table: doctor
-- Stores doctor information
-- ============================================
CREATE TABLE doctor (
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_name VARCHAR(100) NOT NULL,
    gender ENUM('M', 'F', 'Other') NOT NULL,
    title VARCHAR(50) NOT NULL COMMENT 'e.g., Chief Physician, Attending Physician',
    department_id INT NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    specialization VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES department(department_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Doctor information table';

-- ============================================
-- Table: registration
-- Stores patient registration records
-- status: 0=未缴费(Unpaid), 1=待就诊(Waiting), 2=已完成(Completed)
-- ============================================
CREATE TABLE registration (
    registration_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    department_id INT NOT NULL,
    doctor_id INT,
    registration_date DATE NOT NULL,
    registration_time TIME NOT NULL,
    status TINYINT NOT NULL DEFAULT 0 COMMENT '0:未缴费, 1:待就诊, 2:已完成',
    fee DECIMAL(10, 2) NOT NULL DEFAULT 10.00,
    chief_complaint TEXT COMMENT 'Main complaint or symptoms',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (department_id) REFERENCES department(department_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctor(doctor_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CHECK (status IN (0, 1, 2)),
    CHECK (fee >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Registration records table';

-- ============================================
-- Table: payment
-- Stores payment records
-- payment_status: 0=未支付(Unpaid), 1=已支付(Paid)
-- ============================================
CREATE TABLE payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    registration_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    payment_method ENUM('Cash', 'Card', 'Insurance', 'Online') NOT NULL,
    payment_status TINYINT NOT NULL DEFAULT 0 COMMENT '0:未支付, 1:已支付',
    payment_date DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (registration_id) REFERENCES registration(registration_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CHECK (payment_status IN (0, 1)),
    CHECK (amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Payment records table';

-- ============================================
-- Table: drug
-- Stores drug inventory information
-- ============================================
CREATE TABLE drug (
    drug_id INT AUTO_INCREMENT PRIMARY KEY,
    drug_name VARCHAR(200) NOT NULL,
    drug_code VARCHAR(50) UNIQUE NOT NULL,
    specification VARCHAR(100) NOT NULL COMMENT 'e.g., 500mg, 10ml',
    manufacturer VARCHAR(200) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    stored_quantity INT NOT NULL DEFAULT 0,
    expiry_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (stored_quantity >= 0),
    CHECK (unit_price > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Drug inventory table';

-- ============================================
-- Table: prescription
-- Stores prescription details
-- ============================================
CREATE TABLE prescription (
    prescription_id INT AUTO_INCREMENT PRIMARY KEY,
    registration_id INT NOT NULL,
    drug_id INT NOT NULL,
    quantity INT NOT NULL,
    dosage VARCHAR(100) NOT NULL COMMENT 'e.g., 1 tablet 3 times daily',
    duration_days INT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (registration_id) REFERENCES registration(registration_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (drug_id) REFERENCES drug(drug_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CHECK (quantity > 0),
    CHECK (duration_days > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Prescription details table';

-- ============================================
-- Stored Procedure: sp_create_registration
-- Creates a registration record and its corresponding payment record
-- Input: patient_id, department_id, payment_method (optional, defaults to 'Cash')
-- Output: registration_id
-- ============================================
DELIMITER //

CREATE PROCEDURE sp_create_registration(
    IN p_patient_id INT,
    IN p_department_id INT,
    IN p_payment_method ENUM('Cash', 'Card', 'Insurance', 'Online'),
    OUT p_registration_id INT
)
BEGIN
    DECLARE v_fee DECIMAL(10, 2) DEFAULT 10.00;
    DECLARE v_registration_date DATE;
    DECLARE v_registration_time TIME;
    DECLARE v_payment_method ENUM('Cash', 'Card', 'Insurance', 'Online');
    
    -- Set default payment method if NULL
    SET v_payment_method = IFNULL(p_payment_method, 'Cash');
    
    -- Get current date and time
    SET v_registration_date = CURDATE();
    SET v_registration_time = CURTIME();
    
    -- Insert registration record with status 0 (未缴费)
    INSERT INTO registration (patient_id, department_id, registration_date, registration_time, status, fee)
    VALUES (p_patient_id, p_department_id, v_registration_date, v_registration_time, 0, v_fee);
    
    -- Get the newly created registration_id
    SET p_registration_id = LAST_INSERT_ID();
    
    -- Create corresponding payment record with payment_status 0 (未支付)
    INSERT INTO payment (registration_id, amount, payment_method, payment_status)
    VALUES (p_registration_id, v_fee, v_payment_method, 0);
END //

DELIMITER ;

-- ============================================
-- Trigger: trig_reduce_stock
-- Automatically reduces drug stock when prescription is added
-- Raises exception if stock is insufficient
-- ============================================
DELIMITER //

CREATE TRIGGER trig_reduce_stock
AFTER INSERT ON prescription
FOR EACH ROW
BEGIN
    DECLARE v_current_stock INT;
    DECLARE v_drug_name VARCHAR(200);
    DECLARE v_error_message VARCHAR(1000);
    DECLARE v_rows_affected INT;
    
    -- Get current stock for the drug
    SELECT stored_quantity, drug_name INTO v_current_stock, v_drug_name
    FROM drug
    WHERE drug_id = NEW.drug_id;
    
    -- Check if drug exists
    IF v_current_stock IS NULL THEN
        SET v_error_message = CONCAT('Drug with ID ', NEW.drug_id, ' does not exist');
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = v_error_message,
            MYSQL_ERRNO = 1002;
    END IF;
    
    -- Check if stock is sufficient
    IF v_current_stock < NEW.quantity THEN
        SET v_error_message = CONCAT('Insufficient stock for drug "', v_drug_name, '". Required: ', NEW.quantity, ', Available: ', v_current_stock);
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = v_error_message,
            MYSQL_ERRNO = 1001;
    END IF;
    
    -- Atomically reduce stock with validation (prevents race conditions)
    UPDATE drug
    SET stored_quantity = stored_quantity - NEW.quantity
    WHERE drug_id = NEW.drug_id
    AND stored_quantity >= NEW.quantity;
    
    -- Verify the update succeeded
    SET v_rows_affected = ROW_COUNT();
    IF v_rows_affected = 0 THEN
        SET v_error_message = CONCAT('Failed to reduce stock for drug "', v_drug_name, '". Stock may have been reduced by another transaction.');
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = v_error_message,
            MYSQL_ERRNO = 1003;
    END IF;
END //

DELIMITER ;

-- ============================================
-- Trigger: trig_update_reg_status
-- Automatically updates registration status when payment is completed
-- Updates status from 0 (未缴费) to 1 (待就诊) when payment_status changes to 1 (已支付)
-- ============================================
DELIMITER //

CREATE TRIGGER trig_update_reg_status
AFTER UPDATE ON payment
FOR EACH ROW
BEGIN
    -- If payment status changed from 0 to 1 (from unpaid to paid)
    IF OLD.payment_status = 0 AND NEW.payment_status = 1 THEN
        UPDATE registration
        SET status = 1  -- 待就诊 (Waiting for consultation)
        WHERE registration_id = NEW.registration_id;
    END IF;
END //

DELIMITER ;

-- ============================================
-- Test Data
-- Inserting test data with logical relationships
-- ============================================

-- Insert test data for patient table
INSERT INTO patient (patient_name, gender, date_of_birth, phone, address, id_card) VALUES
('张三', 'M', '1985-06-15', '13812345678', '北京市朝阳区建国路100号', '110101198506151234'),
('李四', 'F', '1990-03-22', '13987654321', '上海市浦东新区陆家嘴金融街88号', '310115199003220987'),
('王五', 'M', '1978-11-08', '13698745632', '广州市天河区天河路208号', '440106197811081122'),
('赵六', 'F', '1995-08-30', '13556781234', '深圳市南山区科技园南路66号', '440305199508303344'),
('孙七', 'M', '1982-12-18', '13745698012', '成都市武侯区人民南路120号', '510107198212185566');

-- Insert test data for department table
INSERT INTO department (department_name, description, location, phone) VALUES
('内科', '内科疾病诊疗，包括呼吸、消化、心血管等', '门诊楼2楼', '010-88881001'),
('外科', '外科手术及术后康复治疗', '门诊楼3楼', '010-88881002'),
('儿科', '儿童疾病诊疗及儿童保健', '门诊楼1楼', '010-88881003'),
('妇产科', '妇科疾病及产科服务', '门诊楼4楼', '010-88881004'),
('骨科', '骨科疾病及创伤治疗', '门诊楼5楼', '010-88881005');

-- Insert test data for doctor table
INSERT INTO doctor (doctor_name, gender, title, department_id, phone, email, specialization) VALUES
('陈医生', 'M', '主任医师', 1, '13901234567', 'chen.doctor@hospital.com', '心血管内科'),
('刘医生', 'F', '副主任医师', 2, '13902345678', 'liu.doctor@hospital.com', '普通外科'),
('杨医生', 'F', '主治医师', 3, '13903456789', 'yang.doctor@hospital.com', '儿科常见病'),
('周医生', 'M', '主任医师', 4, '13904567890', 'zhou.doctor@hospital.com', '产科'),
('吴医生', 'M', '副主任医师', 5, '13905678901', 'wu.doctor@hospital.com', '关节外科');

-- Insert test data for drug table
INSERT INTO drug (drug_name, drug_code, specification, manufacturer, unit_price, stored_quantity, expiry_date) VALUES
('阿莫西林胶囊', 'AMX001', '250mg*24粒/盒', '华北制药集团有限公司', 15.50, 1000, '2026-12-31'),
('布洛芬片', 'IBU001', '0.2g*20片/盒', '中美天津史克制药有限公司', 12.00, 800, '2026-06-30'),
('头孢克肟颗粒', 'CEF001', '50mg*6袋/盒', '广州白云山制药股份有限公司', 28.50, 500, '2025-12-31'),
('复方氨酚烷胺片', 'FPA001', '12片/盒', '石药集团欧意药业有限公司', 8.90, 1200, '2026-03-31'),
('硫酸氨基葡萄糖胶囊', 'GLU001', '0.24g*20粒/盒', '浙江海正药业股份有限公司', 45.00, 600, '2026-09-30');

-- Insert test data for registration table
-- Note: These registrations start with status 0 (未缴费)
INSERT INTO registration (patient_id, department_id, doctor_id, registration_date, registration_time, status, fee, chief_complaint) VALUES
(1, 1, 1, '2025-12-15', '09:30:00', 0, 10.00, '胸闷气短，活动后加重'),
(2, 2, 2, '2025-12-15', '10:00:00', 0, 10.00, '右下腹疼痛2天'),
(3, 3, 3, '2025-12-16', '14:30:00', 0, 10.00, '小儿发热咳嗽3天'),
(4, 4, 4, '2025-12-16', '15:00:00', 0, 10.00, '停经40天，早孕检查'),
(5, 5, 5, '2025-12-17', '08:30:00', 0, 10.00, '左膝关节疼痛肿胀1周');

-- Insert test data for payment table
-- Note: These payments start with payment_status 0 (未支付)
INSERT INTO payment (registration_id, amount, payment_method, payment_status) VALUES
(1, 10.00, 'Cash', 0),
(2, 10.00, 'Card', 0),
(3, 10.00, 'Insurance', 0),
(4, 10.00, 'Online', 0),
(5, 10.00, 'Cash', 0);

-- ============================================
-- Test Examples for Stored Procedure and Triggers
-- ============================================

-- Example 1: Test stored procedure sp_create_registration
-- This will create a new registration and payment record
-- Uncomment the following lines to test:
/*
-- With default payment method (Cash)
CALL sp_create_registration(1, 1, NULL, @new_reg_id);
SELECT @new_reg_id AS 'New Registration ID';
SELECT * FROM registration WHERE registration_id = @new_reg_id;
SELECT * FROM payment WHERE registration_id = @new_reg_id;

-- With specified payment method
CALL sp_create_registration(2, 2, 'Card', @new_reg_id2);
SELECT @new_reg_id2 AS 'New Registration ID 2';
SELECT * FROM registration WHERE registration_id = @new_reg_id2;
SELECT * FROM payment WHERE registration_id = @new_reg_id2;
*/

-- Example 2: Test trigger trig_update_reg_status
-- Update payment status to paid, which should update registration status
-- Uncomment the following lines to test:
/*
UPDATE payment SET payment_status = 1, payment_date = NOW() WHERE payment_id = 1;
SELECT * FROM registration WHERE registration_id = 1;  -- Should show status = 1
*/

-- Example 3: Test trigger trig_reduce_stock
-- First, let's complete a registration and add a prescription
-- Uncomment the following lines to test:
/*
-- Complete the payment first
UPDATE payment SET payment_status = 1, payment_date = NOW() WHERE payment_id = 2;
UPDATE registration SET status = 2 WHERE registration_id = 2;  -- Mark as completed

-- Add prescription (this will reduce drug stock)
INSERT INTO prescription (registration_id, drug_id, quantity, dosage, duration_days, notes)
VALUES (2, 1, 2, '1粒，每日3次，饭后服用', 7, '注意过敏反应');

-- Check drug stock (should be reduced by 2)
SELECT drug_name, stored_quantity FROM drug WHERE drug_id = 1;
*/

-- Example 4: Test insufficient stock error
-- Try to prescribe more drugs than available in stock
-- Uncomment the following lines to test:
/*
INSERT INTO prescription (registration_id, drug_id, quantity, dosage, duration_days)
VALUES (1, 1, 5000, '按医嘱', 7);  -- This should fail due to insufficient stock
*/

-- ============================================
-- Verification Queries
-- ============================================

-- View all tables structure
SHOW TABLES;

-- View registration records with status
SELECT 
    r.registration_id,
    p.patient_name,
    d.department_name,
    r.registration_date,
    CASE r.status
        WHEN 0 THEN '未缴费'
        WHEN 1 THEN '待就诊'
        WHEN 2 THEN '已完成'
    END AS status_text
FROM registration r
JOIN patient p ON r.patient_id = p.patient_id
JOIN department d ON r.department_id = d.department_id;

-- View payment records with status
SELECT 
    pay.payment_id,
    r.registration_id,
    p.patient_name,
    pay.amount,
    pay.payment_method,
    CASE pay.payment_status
        WHEN 0 THEN '未支付'
        WHEN 1 THEN '已支付'
    END AS payment_status_text
FROM payment pay
JOIN registration r ON pay.registration_id = r.registration_id
JOIN patient p ON r.patient_id = p.patient_id;

-- View drug inventory
SELECT drug_name, specification, stored_quantity, unit_price, expiry_date
FROM drug
ORDER BY drug_name;
