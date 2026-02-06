import secrets
import smtplib
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import jwt
from mysql.connector import Error
import hashlib 
from flask_cors import CORS
#for forgot password
from flask_mail import Mail, Message
#for uploading image file
import urllib.request
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import json
import random
from datetime import datetime
#for pass
import re
from decimal import Decimal
from flask import flash, redirect
#for otp
import requests
import uuid
from flask_bcrypt import Bcrypt

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
bcrypt = Bcrypt(app)




# Flask-Mail Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)
tokens_store = {}

#Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),    
        user=os.getenv('DB_USER'),        
        password=os.getenv('DB_PASSWORD'),        
        database=os.getenv('DB_NAME')  
    )


# MASKING FEEDBACK EMAIL WITH *
@app.template_filter('mask_email')
def mask_email(email):
    try:
        name, domain = email.split('@')
        return name[:2] + '*******@' + domain
    except:
        return email



# Route to handle the AJAX request and fetch discount amount
@app.route('/get-discount', methods=['POST'])
def get_discount():
    if request.is_json:
        voucher_code = request.json.get('voucher_code')

        # Query to get the discount amount from the database
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT discount_amount FROM vouchers WHERE code = %s AND is_status = 1", (voucher_code,))
        result = cursor.fetchone()
        connection.close()

        if result:
            discount_amount = result[0]
            return jsonify({"discount_amount": discount_amount})
        else:
            return jsonify({"error": "Invalid Voucher Code or Inactive Voucher"}), 400
    else:
        return jsonify({"error": "Request must be JSON"}), 400

# Function to insert user logs
def insert_user_log(user_id, user_type, activity_description):
    try:
        # Get the database connection
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # SQL query to insert the log
        query = """
        INSERT INTO user_logs (user_id, user_type, log_date, activity_description)
        VALUES (%s, %s, %s, %s)
        """
        log_date = datetime.now()
        values = (user_id, user_type, log_date, activity_description)
        
        # Execute query and commit
        cursor.execute(query, values)
        connection.commit()
        
        # Close the connection
        cursor.close()
        connection.close()
        return True, "Log entry added successfully!"
    except Exception as e:
        return False, str(e)

@app.route('/user_logs', methods=['GET', 'POST'])
def user_logs():
    try:
        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get search term and user type from the form (if any)
        search_term = request.args.get('search', '')  # Default to empty if not provided
        user_type_filter = request.args.get('user_type', '')  # Default to empty if not provided

        # Base query
        query = "SELECT * FROM user_logs WHERE 1=1"

        # List to hold the parameters for the query
        params = []

        # If search term is provided, add to the query and parameters
        if search_term:
            query += " AND (user_id LIKE %s OR activity_description LIKE %s)"
            params.extend([f'%{search_term}%', f'%{search_term}%'])

        # If user type is provided, add to the query and parameters
        if user_type_filter:
            query += " AND user_type = %s"
            params.append(user_type_filter)

        # Execute the query with the parameters
        cursor.execute(query, params)

        # Fetch the results
        logs = cursor.fetchall()

        # Close database connection
        cursor.close()
        conn.close()

        # Render the template with the logs
        return render_template('admin/user_logs.html', logs=logs)

    except mysql.connector.Error as err:
        return f"Error fetching logs: {err}"



@app.route('/seller/vouchers', methods=['GET'])
def seller_vouchers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch vouchers for the seller (assuming `seller_id` is available in the session)
    cursor.execute('SELECT * FROM vouchers WHERE sellerID = %s', (session['seller_id'],))
    vouchers = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('seller/seller_vouchers.html', vouchers=vouchers)

@app.route('/seller/vouchers/add', methods=['POST'])
def add_voucher():
    code = request.form['voucher_code']
    discount_amount = request.form['discount_amount']
    min_spend = request.form['min_spend']
    expiration_date = request.form['expiration_date']
    code_limit = request.form['code_limit']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO vouchers (sellerID, code, discount_amount, min_spend, expiration_date, is_active, code_limit) 
                      VALUES (%s, %s, %s, %s, %s, 1, %s)''', 
                   (session['seller_id'], code, discount_amount, min_spend, expiration_date,code_limit))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Voucher added successfully.')
    return redirect('/seller/vouchers')


# Also make sure to handle the code_limit in other relevant routes (e.g., update and delete)


@app.route('/seller/vouchers/update/<int:voucher_id>', methods=['POST'])
def update_voucher(voucher_id):
    action = request.form['action']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if action == 'toggle':
        # Toggle is_active value between 1 (active) and 0 (inactive)
        cursor.execute('''UPDATE vouchers SET is_active = NOT is_active 
                          WHERE id = %s AND sellerID = %s''', 
                       (voucher_id, session['seller_id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Voucher updated successfully.')
    return redirect('/seller/vouchers')

@app.route('/seller/vouchers/delete/<int:voucher_id>', methods=['POST'])
def delete_voucher(voucher_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vouchers WHERE id = %s AND sellerID = %s', 
                   (voucher_id, session['seller_id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Voucher deleted successfully.')
    return redirect('/seller/vouchers')





@app.route('/admin/user-management', methods=['GET', 'POST'])
def user_management():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        account_type = request.form.get('account_type')
        account_id = request.form.get('account_id')
        account_email = request.form.get('account_email')  # Get the email from the form
        action = request.form.get('action')
        rejection_reason = request.form.get('reason') if action == 'Reject' else None

        subject = ''
        body = ''

        # Handle buyer account approval/rejection
        if account_type == 'buyer':
            if action == 'Approve':
                cursor.execute('UPDATE buyer_account SET status = "Approved" WHERE id_no = %s', (account_id,))
                subject = 'Your Buyer Account has been Approved'
                body = 'Dear User, your buyer account has been approved successfully.'
            elif action == 'Reject':
                cursor.execute('UPDATE buyer_account SET status = "Rejected", reason = %s WHERE id_no = %s', (rejection_reason, account_id))
                subject = 'Your Buyer Account has been Rejected'
                body = f'Dear User, your buyer account has been rejected. Reason: {rejection_reason}'

        # Handle seller account approval/rejection
        elif account_type == 'seller':
            if action == 'Approve':
                cursor.execute('UPDATE seller_account SET status = "Approved" WHERE sellerID = %s', (account_id,))
                subject = 'Your Seller Account has been Approved'
                body = 'Dear User, your seller account has been approved successfully.'
            elif action == 'Reject':
                cursor.execute('UPDATE seller_account SET status = "Rejected", reason = %s WHERE sellerID = %s', (rejection_reason, account_id))
                subject = 'Your Seller Account has been Rejected'
                body = f'Dear User, your seller account has been rejected. Reason: {rejection_reason}'
         # Handle courier account approval/rejection
        elif account_type == 'rider':
            if action == 'Approve':
                cursor.execute('UPDATE rider_account SET status = "Approved" WHERE id_no = %s', (account_id,))
                subject = 'Your Rider Account has been Approved'
                body = 'Dear User, your rider account has been approved successfully.'
            elif action == 'Reject':
                cursor.execute('UPDATE rider_account SET status = "Rejected", reason = %s WHERE id_no = %s', (rejection_reason, account_id))
                subject = 'Your Rider Account has been Rejected'
                body = f'Dear User, your rider account has been rejected. Reason: {rejection_reason}'

        # Commit the changes to the database
        conn.commit()

        # Send the email to the user
        msg = Message(subject, sender='valdellon44@gmail.com', recipients=[account_email])
        msg.body = body
        try:
            mail.send(msg)
            print('sent email')
        except Exception as e:
            print(f"Error sending email: {e}")

        # Redirect back to the user management page
        return redirect(url_for('user_management'))

    # Fetch all pending buyer and seller accounts
    cursor.execute('''
    SELECT ba.*, addr.* 
    FROM buyer_account ba
    LEFT JOIN buyer_address addr ON ba.address_id = addr.address_id
    WHERE ba.status = "Pending" AND ba.id_no = addr.buyer_id
''')
    buyers = cursor.fetchall()

    cursor.execute('''
    SELECT sa.*, addr.* 
    FROM seller_account sa
    LEFT JOIN seller_address addr ON sa.address_id = addr.address_id
    WHERE sa.status = "Pending" AND sa.sellerID = addr.seller_id
''')
    sellers = cursor.fetchall()

    cursor.execute('''
    SELECT ra.*, addr.* 
    FROM rider_account ra
    LEFT JOIN rider_address addr ON ra.address_id = addr.address_id
    WHERE ra.status = "Pending" AND ra.id_no = addr.rider_id
''')
    riders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/user_management.html', buyers=buyers, sellers=sellers, riders=riders)

def send_email_via_flask_mail(to_email, subject, body):
    msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[to_email])
    msg.body = body
    try:
        # Send the email
        mail.send(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")
        
        
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        # Check if email exists in the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM buyer_account WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            # Send reset email
            send_reset_email(email)
            flash("A password reset email has been sent. Please check your email.", "success")
        else:
            flash("Email not found.", "error")
            return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

def send_reset_email(email):

    token = secrets.token_urlsafe(32)  # Generate a secure token
    tokens_store[token] = email  # Store token and associated email
    reset_link = url_for('reset_password', token=token, _external=True)
    msg = Message("Password Reset Request",
                  sender=os.getenv('MAIL_SENDER'),
                  recipients=[email])
    msg.body = f"Please use the following link to reset your password: {reset_link}"
    mail.send(msg)

def get_email_from_token(token):
    return tokens_store.get(token)  # Get the email associated with the token

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        new_password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        email = get_email_from_token(token)  # Get email using the token
        
        if email:
            # Update the password in the buyer_account table
            cursor.execute("UPDATE buyer_account SET password = %s WHERE email = %s", (new_password, email))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Your password has been reset successfully.", "success")
        else:
            flash("Invalid token.", "error")
            return redirect(url_for('forgot_password'))
    
    return render_template('reset_password.html')



#LOGIN
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if email == "test@example.com" and password == "password123":
            flash('Login successful!', 'success')
            return redirect(url_for('index'))  
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('log.html')   

@app.route('/admindashboard')
def admin_dashboard():
    # Get the commission from the admin_account table
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the commission from the admin_account table
    cursor.execute('''SELECT commission FROM admin_account WHERE adminID = 1''')
    commission = cursor.fetchone()['commission']  # Fetch the commission value

    # Count the total seller accounts where status is 'approve'
    cursor.execute('''SELECT COUNT(*) AS total_sellers_approved
                      FROM seller_account
                      WHERE status = "Approved"''')
    total_sellers_approved = cursor.fetchone()['total_sellers_approved']  # Get the count value
    
    
    cursor.execute('''SELECT * FROM reports ORDER BY created_at LIMIT 5''')
    reports = cursor.fetchall()  # Fetch t 
    
    cursor.execute('''SELECT COUNT(*) AS total_reports FROM reports''')
    total_reports = cursor.fetchone()['total_reports']  # Get the count value for all reports
    # Close the connection
    cursor.close()
    conn.close()

    # Pass the commission and total_sellers_approved to the template
    return render_template('admin/admin.html',reports=reports, commission=commission, total_sellers_approved=total_sellers_approved, total_reports=total_reports)

@app.route('/adminreports')
def admin_reports():
    # Get the commission from the admin_account table
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the commission from the admin_account table
    
    
    cursor.execute('''SELECT * FROM reports''')
    reports = cursor.fetchall()  # Fetch t 
    # Close the connection
    cursor.close()
    conn.close()

    # Pass the commission and total_sellers_approved to the template
    return render_template('admin/adminreports.html',reports=reports)

@app.route('/login', methods=['POST'])
def login_submit():
    email = request.form['email']
    password = request.form['password']

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check for account in buyer, seller, and admin tables
    account_types = [
        ("buyer_account", "id_no", "index", "buyer"),
        ("seller_account", "sellerID", "sellerdashboard", "seller"),
        ("admin_account", "adminID", "admin_dashboard", "admin"),
    ]

    for table, id_field, dashboard, role in account_types:
        cursor.execute(f"SELECT * FROM {table} WHERE email = %s", (email,))
        account = cursor.fetchone()

        if account:
            # Check password
            if account['password'] == password:
                # Check account status
                status = account.get('status', 'Approved')  # Default to Approved for admin accounts
                if status == "Approved":
                    session['user_name'] = account['name']
                    session['user_email'] = account['email']
                    
                    session[f'{role}_id'] = account[id_field]

                    # Specifically for buyers, set buyer_id
                    if role == "buyer":
                        session['buyer_id'] = account[id_field]
                    elif role == "seller":
                        session['seller_id'] = account[id_field]
                    cursor.close()
                    conn.close()
                    return redirect(url_for(dashboard))
                elif status == "Pending":
                    flash(f'Your account is pending approval. Please wait for an update via email.', "error")
                elif status == "Rejected":
                    flash(f'Your account has been rejected. Please check your email for details.', "error")
                else:
                    flash(f'Unexpected account status: {status}.', "error")
                return redirect(url_for('login'))
            else:
                flash('Incorrect password. Please try again.', "error")
                return redirect(url_for('login'))

    # No account found
    flash('Email not found. Please check your email or password.', "error")
    cursor.close()
    conn.close()
    return redirect(url_for('login'))


        
    

#Route for the registration page
@app.route('/register')
def register():
    return render_template('reg.html')

#Route to handle form submission REGISTER
@app.route('/submit_form', methods=['POST'])
def submit_form():
    name = request.form['name']
    gender = request.form['gender'] 
    dateofbirth = request.form['dateofbirth']
    number = request.form['number']
    email = request.form['email']
    password = request.form['password']
    confirmpassword = request.form['confirmpassword']
    region = request.form.get('region_text', request.form.get('region'))
    province = request.form.get('province_text', request.form.get('province'))
    city = request.form.get('city_text', request.form.get('city'))
    barangay = request.form.get('barangay_text', request.form.get('barangay'))

    validID = request.files['validID']


    try:
        dob = datetime.strptime(dateofbirth, '%Y-%m-%d')
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            flash('You must be at least 18 years old to register.', 'error')
            return render_template('reg.html', form=request.form)
    except ValueError:
        flash('Invalid date of birth format. Please use YYYY-MM-DD.', 'error')
        return render_template('reg.html', form=request.form)
    

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Check if the email already exists
    cursor.execute("SELECT * FROM buyer_account WHERE email = %s", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        flash('This email is already registered. Please use a different email.', "error")
        return render_template('reg.html', form=request.form)

    # Confirm passwords match
    if confirmpassword != password:
        flash('Password does not match. Please try again.', "error")
        return render_template('reg.html', form=request.form)

    # Validate mobile number
    if not number.isdigit() or len(number) != 11:
        flash('Please enter a valid mobile number.', 'error')
        return render_template('reg.html', form=request.form)

    # Password requirements
    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$'
    if not re.match(password_regex, password):
        flash('Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, and a number.', 'error')
        return render_template('reg.html', form=request.form)

     # Save valid ID file
    if validID and allowed_file(validID.filename):  # Ensure valid file extension
        image_path = f'static/assets/IDs/{secure_filename(validID.filename)}'
        validID.save(image_path)
    else:
        flash('Invalid ID upload. Only images are allowed.', 'error')
        return render_template('reg.html', form=request.form)


    try:

        # Insert into buyer_account
        cursor.execute("""INSERT INTO buyer_account (name, gender, dateofbirth, mobile_no, email, password, image_path, status) VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending')""",
        (name, gender, dateofbirth, number, email, password, image_path)) 
        conn.commit()

        buyer_id = cursor.lastrowid

        #insert into buyer_address
        cursor.execute("""INSERT INTO buyer_address (region, province, city, brgy, buyer_id) VALUES (%s, %s, %s, %s, %s)""", 
                       (region, province, city, barangay, buyer_id))
        conn.commit()

        address_id = cursor.lastrowid

        cursor.execute("UPDATE buyer_account SET address_id = %s WHERE id_no = %s", (address_id, buyer_id))
        conn.commit()

        flash('Registration successful! Your account is pending approval.', 'success')
        return redirect(url_for('register'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return render_template('reg.html', form=request.form)


# Helper Function for IMAGE File Validation
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

@app.route('/logout')
def logout():

    session.clear()  
    return redirect(url_for('login'))  #Redirect to the login page

@app.route('/index')
def index():

        if 'user_name' in session:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)


             #SEARCH

            # Get search term from the query string
            search_term = request.args.get('search', '').strip()

            # Base SQL query
            base_query = 'SELECT * FROM producttbl WHERE qty > 0'
            
            # Filter by search term if provided
            if search_term:
                search_query = f" AND (prName LIKE %s OR brand LIKE %s OR prType LIKE %s)"
                search_values = [f"%{search_term}%"] * 3
            else:
                search_query = ''
                search_values = []

            # Fetch Team Sports products
            cursor.execute(base_query + ' AND prType="Team Sports"' + search_query, search_values)
            products = cursor.fetchall()

            # Fetch other categories similarly
            categories = ["Water Sports", "Camping & Hiking", "Cycling & Biking", "Fitness Equipments", "Sports Apparel"]
            products_by_category = {}
            for category in categories:
                cursor.execute(base_query + f' AND prType=%s' + search_query, [category] + search_values)
                products_by_category[category] = cursor.fetchall()



            cursor.execute('SELECT * FROM producttbl WHERE prType="Team Sports" AND qty > 0')
            products = cursor.fetchall()
            cursor.close()
            conn.close()
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM producttbl WHERE prType="Water Sports" AND qty > 0')
            products_water = cursor.fetchall()
            cursor.close()
            conn.close()
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM producttbl WHERE prType="Camping & Hiking" AND qty > 0')
            products_CK = cursor.fetchall()
            cursor.close()
            conn.close()
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM producttbl WHERE prType="Cycling & Biking" AND qty > 0')
            products_CB = cursor.fetchall()
            cursor.close()
            conn.close()
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM producttbl WHERE prType="Fitness Equipments" AND qty > 0')
            products_FE = cursor.fetchall()
            cursor.close()
            conn.close()
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM producttbl WHERE prType="Sports Apparel" AND qty > 0')
            products_SA = cursor.fetchall()
            cursor.close()
            conn.close()
            # Get updated cart count (total quantity)
            user_email=session['user_email']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(product_id) FROM carttbl WHERE user_id = %s', (user_email,))
            #cursor.execute('SELECT SUM(quantity) FROM carttbl WHERE user_id = "roswelljamesvitaliz@gmail.com"')
            cart_count = cursor.fetchone()[0] or 0  # Use 0 if no items in the cart
            cursor.close()
            return render_template('index.html', products=products, user_name=session['user_name'], cart_count=cart_count, 
                                   products_water=products_by_category["Water Sports"],
            products_CK=products_by_category["Camping & Hiking"],
            products_CB=products_by_category["Cycling & Biking"],
            products_FE=products_by_category["Fitness Equipments"],
            products_SA=products_by_category["Sports Apparel"],
            search_term=search_term) 
        else:
            return redirect(url_for('login'))  #Redirect to login if not logged in


#CART
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_email = session['user_email']  # Get logged-in user's ID
    data = request.get_json()
    quantity = int(data.get('quantity', 1))  # Use 1 as default if no quantity provided

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch the product price and qty from the database
    cursor.execute('SELECT prPrice, qty, sellerID FROM producttbl WHERE productID = %s', (product_id,))
    product = cursor.fetchone()

    if product:
        price = product[0]  # Get the product price
        price = price.replace(",", "")  # Remove commas if any
        price = float(price)  # Convert to float
        current_qty = product[1]  # Get the current quantity
        sellerID = product[2]
        if current_qty >= quantity:
            # Calculate the total price for the quantity
            total_price = round(price * quantity, 2)

            # Check if the product is already in the cart
            cursor.execute('SELECT * FROM carttbl WHERE user_id = %s AND product_id = %s', (user_email, product_id))
            existing_item = cursor.fetchone()

            if existing_item:
                # Update the quantity and total price if the item already exists in the cart
                cursor.execute('UPDATE carttbl SET quantity = quantity + %s, total_price = total_price + %s WHERE id = %s',
                               (quantity, total_price, existing_item[0]))
            else:
                # Insert new item with specified quantity and calculated total_price
                cursor.execute('INSERT INTO carttbl (user_id, product_id, quantity, total_price, sellerID) VALUES (%s, %s, %s, %s, %s)',
                               (user_email, product_id, quantity, total_price, sellerID))

            # Update the qty column in producttbl by subtracting the quantity added to the cart
            

            conn.commit()

        else:
            return jsonify({'success': False, 'message': 'Not enough stock available'})

    else:
        return jsonify({'success': False, 'message': 'Product not found'})

    cursor.close()

    # Get the updated cart count
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(product_id) FROM carttbl WHERE user_id = %s', (user_email,))
    cart_count = cursor.fetchone()[0] or 0  # Use 0 if no items in the cart
    cursor.close()
    conn.close()

    return jsonify({'cart_count': cart_count})



@app.route('/update-quantity/<int:product_id>', methods=['POST'])
def update_quantity(product_id):
    data = request.get_json()
    quantity = data.get('quantity')

    if quantity is None or quantity < 1:
        return jsonify({'success': False, 'message': 'Invalid quantity'})

    connection = get_db_connection()
    cursor = connection.cursor()
    
    try:
        # Fetch the product price from the database (remove commas for proper conversion)
        cursor.execute("SELECT prPrice FROM producttbl WHERE productID = %s", (product_id,))
        result = cursor.fetchone()

        if result:
            price = result[0]  # Price is fetched as a string with commas like '1,480.00'
            price = price.replace(",", "")  # Remove commas from price string
            price = float(price)  # Convert to float after removing commas

            # Calculate the new total price based on the updated quantity
            total_price = round(price * quantity, 2)

            # Update the quantity and total price in the cart for this product
            cursor.execute(
                "UPDATE carttbl SET quantity = %s, total_price = %s WHERE product_id = %s",
                (quantity, total_price, product_id)
            )
            connection.commit()

            # Optionally, fetch the updated cart subtotal if needed
            cursor.execute("SELECT SUM(total_price) FROM carttbl")
            cart_subtotal = cursor.fetchone()[0]

            return jsonify({
                'success': True,
                'newPrice': total_price,  # The new total price for this item
                'cartSubtotal': cart_subtotal  # Total cart value
            })
        else:
            return jsonify({'success': False, 'message': 'Product not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        connection.close()





        
@app.route('/cart', methods=['GET', 'POST'])
def cart():
    user_email = session['user_email']  # Get logged-in user's ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get all products in the user's cart
    cursor.execute(''' 
    SELECT p.*, c.quantity, c.total_price
    FROM producttbl p
    JOIN carttbl c ON p.productID = c.product_id
    WHERE c.user_id = %s
''', (user_email,))
    
    cart_products = cursor.fetchall()
    if not cart_products:
        cursor.close()
        conn.close()
        print("Cart is empty for user:", user_email)
        return render_template('cart.html', cart_products=[], vouchers=[], subtotal=0, handling_fee=0, total=0, cart_count=0)
   
    # Convert prPrice to float for each product
    for product in cart_products:
        product['prPrice'] = float(product['prPrice'].replace(',', ''))  # Remove commas and convert to float
    
    cursor.close()
    conn.close()
    sellerID = product['sellerID']
    session['sellerID'] = sellerID
    # Calculate subtotal, handling fee, and total
    subtotal = sum(product['prPrice'] * product['quantity'] for product in cart_products)
    handling_fee = 79.00  # Example handling fee

    total = subtotal + handling_fee

    # Handle POST request for voucher code
    if request.method == 'POST':
        voucher_code = request.form.get('voucher_code')

        # Validate the voucher code
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT discount_amount, min_spend FROM vouchers WHERE sellerID = %s AND code = %s AND is_active = TRUE AND code_limit = 0', (voucher_code,sellerID,))
        voucher = cursor.fetchone()

        #if voucher:
         #   discount_amount = float(voucher['discount_amount'])
          #  total -= discount_amount  # Subtract discount from total
           # total = max(total, 0)  # Ensure total doesn't go below 0
        # else:
          #  discount_amount = 0.0
        if voucher:
            discount_amount = float(voucher['discount_amount'])
            min_spend = float(voucher.get('min_spend', 0))  # Default to 0 if not found

            if total >= min_spend:  # Check if total meets or exceeds the minimum spend
                total -= discount_amount  # Subtract discount from total
                total = max(total, 0)  # Ensure total doesn't go below 0
            else:
                print(f"Total {total} is less than the minimum spend {min_spend}, voucher not applied.")
                discount_amount = 0.0  # No discount if condition isn't met
        else:
            discount_amount = 0.0
        cursor.close()
        conn.close()

        # Return the updated total as JSON response for AJAX
        return jsonify({
            'total': total
        })

    # Get updated cart count (total quantity)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(product_id) FROM carttbl WHERE user_id = %s', (user_email,))
    cart_count = cursor.fetchone()[0] or 0  # Use 0 if no items in the cart
    cursor.close()

    conn = get_db_connection()
    cursor = conn.cursor()

    # SQL query to fetch voucher codes that are still valid
    cursor.execute('''
    SELECT code 
    FROM vouchers 
    WHERE sellerID = %s 
      AND is_active = 1 
      AND expiration_Date >= CURDATE() 
      AND code_limit > 0
''', (sellerID,))

    vouchers = cursor.fetchall()  # Fetch all rows

    cursor.close()
    conn.close()

    # Render cart template with product details
    return render_template('cart.html',vouchers=vouchers, cart_products=cart_products, subtotal=subtotal, handling_fee=handling_fee, total=total, cart_count=cart_count)


# Delete from cart
@app.route('/delete_from_cart', methods=['POST'])
def delete_from_cart():

    product_id = request.form['product_id']

    if not product_id:
        flash('Product ID is missing.')
        return redirect(url_for('cart'))

    print(f"Attempting to delete product")  # Debugging line
    user_email = session['user_email']  # Get logged-in user's ID
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete the product from the cart
        cursor.execute('DELETE FROM carttbl WHERE user_id = %s AND product_id = %s', (user_email, product_id,))
        conn.commit()
    
        # Get updated cart count (total quantity)
        cursor.execute('SELECT COUNT(product_id) FROM carttbl WHERE user_id = %s', (user_email,))
        cart_count = cursor.fetchone()[0] or 0  # Use 0 if no items in the cart
        cursor.close()
        conn.close()

        print(f"Updated cart count: {cart_count}")  # Debugging line
        

    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect('/cart')


#STATUS UPDATE FOR STATUS HISTORY IN ORDERS
def update_order_status(order_id, new_status):
    print(f"Logging status: {order_id}, {new_status}")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Update current status
        cursor.execute("""
            UPDATE cotbl SET status = %s WHERE orderID = %s
        """, (new_status, order_id))

        # 2. Log the status change
        cursor.execute("""
            INSERT INTO status_history (orderID, status, updated_at)
            VALUES (%s, %s, NOW())
        """, (order_id, new_status))

        conn.commit()
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        cursor.close()
        conn.close()



@app.route('/checkout', methods=['POST'])
def checkout():
    user_email = session['user_email']  # Get logged-in user's email
    if request.method == 'POST':
        selected_products = request.form.getlist('selected_products')  # Get list of selected product IDs
        print("Selected products:", selected_products)

    if not selected_products:
        flash("No products selected for checkout.")
        return redirect('/cart')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    sellerID = session.get('sellerID')
    
    voucher_code = request.form.get('voucher_code', '').strip()  # Get voucher code
    discount_amount = 0.0
    min_spend = 0.0

    if voucher_code:
        cursor.execute('''SELECT discount_amount, min_spend, code_limit 
                          FROM vouchers 
                          WHERE code = %s AND sellerID = %s AND is_active = TRUE 
                          AND expiration_date >= CURDATE() AND code_limit > 0''', 
                       (voucher_code, sellerID))
        voucher = cursor.fetchone()
        
        if voucher:
            discount_amount = float(voucher['discount_amount'])
            min_spend = float(voucher['min_spend'])
            cursor.execute('''UPDATE vouchers SET code_limit = code_limit - 1 
                              WHERE sellerID = %s AND code = %s''', 
                           (sellerID, voucher_code))
            print(f"Voucher {voucher_code} limit decremented by 1.")
        else:
            flash("Invalid or expired voucher.")
            return redirect('/cart')

    # Generate a query with placeholders for selected products
    placeholders = ', '.join(['%s'] * len(selected_products))
    query = f'''SELECT c.sellerID, c.product_id, c.quantity, p.prPrice, p.qty
                FROM carttbl c
                JOIN producttbl p ON c.product_id = p.productID
                WHERE c.user_id = %s AND c.product_id IN ({placeholders})'''
    params = (user_email, *selected_products)
    cursor.execute(query, params)
    cart_items = cursor.fetchall()

    if not cart_items:
        flash("Your cart is empty. Add items before checking out.")
        return redirect('/cart')

    for item in cart_items:
        if item['quantity'] > item['qty']:
            flash("Item quantity in cart exceeds available stock.")
            return redirect('/cart')

    # Calculate total cart price (without handling fee)
    total_cart_price = sum(float(item['prPrice'].replace(',', '')) * item['quantity'] for item in cart_items)
    print(f"Total cart price (before handling fee): {total_cart_price}")

    # Apply discount if total_cart_price meets min_spend
    if total_cart_price < min_spend:
        discount_amount = 0.0

    # Add handling fee (applied once for the entire order)
    total_cart_price += 79  # Handling fee of 79 is added once

    # Subtract discount from the total cart price after handling fee
    final_cart_price = total_cart_price - discount_amount
    print(f"Final cart price (after handling fee and discount): {final_cart_price}")

    # Generate a unique order ID
    cursor.execute("SELECT orderID FROM cotbl")
    existing_order_ids = set(row['orderID'] for row in cursor.fetchall())
    while True:
        order_id = random.randint(100000, 999999)
        if order_id not in existing_order_ids:
            break
    session['orderID'] = order_id

    for item in cart_items:
        product_id = item['product_id']
        quantity = item['quantity']
        price = float(item['prPrice'].replace(',', ''))
        total_price = price * quantity
        buyer_price = final_cart_price / len(cart_items)  # Apply average buyer price for each item

        # Insert into cotbl with the buyer's price
        cursor.execute('''INSERT INTO cotbl (user_id, product_id, quantity, price, orderID, sellerID, status) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s)''', 
                       (user_email, product_id, quantity, buyer_price, order_id, sellerID, 'order placed'))
        
        

        # Update product quantity
        cursor.execute('UPDATE producttbl SET qty = qty - %s WHERE productID = %s', 
                       (quantity, product_id))

        # Calculate and add commission for admin
        commission = buyer_price * 0.05
        cursor.execute('SELECT commission FROM admin_account WHERE adminID = 1')
        current_commission = cursor.fetchone()['commission']
        new_commission = Decimal(current_commission) + Decimal(commission)
        cursor.execute('UPDATE admin_account SET commission = %s WHERE adminID = 1', 
                       (new_commission,))

    # Clear only the selected products from the user's cart
    placeholders = ', '.join(['%s'] * len(selected_products))
    cursor.execute(f'DELETE FROM carttbl WHERE user_id = %s AND product_id IN ({placeholders})', 
                   (user_email, *selected_products))
    print("Selected products removed from cart successfully.")

    # Log user activity
    userActivity = f"Buyer {user_email} successfully placed an order."
    insert_user_log(user_email, "buyer", userActivity)
    
    conn.commit()

    #update order history
    update_order_status(order_id, 'order placed')
    
    cursor.close()
    conn.close()

    return redirect('/profile_setting')


@app.route('/checkout_success')
def checkout_success():
    user_email = session['user_email']  # Get logged-in user's email
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the latest status for the user's order
    cursor.execute('''
        SELECT status, id, orderID 
        FROM cotbl 
        WHERE user_id = %s 
        ORDER BY id DESC LIMIT 1
    ''', (user_email,))
    
    result = cursor.fetchone()
    order_status = result['status'] if result else 'order placed'  # Fallback if no orders found
    id = result['id']
    orderID = result['orderID']
    cursor.close()
    conn.close()

    return render_template('checkout_success.html', status=order_status, id=id, orderID = orderID)

# CONFIRM ORDER RECEIVE WEB
@app.route('/update_status', methods=['POST'])
def update_status():
    user_email = session['user_email']  # Get logged-in user's email
    id = request.form['id']  # Get the order ID from the form
    new_status = 'order received'  # Set the new status
    print(f"Order ID: {id}")
    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()
    datenow = datetime.now()
    # Update the status in the database
    cursor.execute('''
        UPDATE cotbl 
        SET status = %s, received = %s 
        WHERE orderID = %s
    ''', (new_status,datenow, id))
    print("updated")
    print(f"User email: {user_email}")
    print(f"Order ID: {id}")
    print(f"Redirection URL: {url_for('profile_setting', status=new_status)}")
    conn.commit()

     #update order history
    update_order_status(id, 'order received')
    
    cursor.close()
    conn.close()
    
    return redirect(url_for('profile_setting', status=new_status))


def mask_email(email):
    try:
        name, domain = email.split('@')
        return name[:2] + '****@' + domain
    except:
        return email


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    user_email = session['user_email']  # Get logged-in user's email
    order_id = request.form['order_id']
    product_id = request.form['product_id']  # Retrieve product_id from the form
    feedback_text = request.form['feedback']
    seller_id = request.form['sellerID']
    reason = request.form.get('report_reason')  # Retrieve the reason for reporting (if provided)
    
    conn = get_db_connection()
    cursor = conn.cursor()

    #MASKING *****
    masked_email = mask_email(user_email)
    # Insert feedback into the database, including product_id
    cursor.execute('''
        INSERT INTO feedback (user_id, order_id, product_id, feedback, sellerID) 
        VALUES (%s, %s, %s, %s, %s)
    ''', (masked_email, order_id, product_id, feedback_text, seller_id))

    # Update the status in the cotbl table to 'feedback done'
    cursor.execute('''
        UPDATE cotbl 
        SET status = 'feedback done' 
        WHERE orderID = %s
    ''', (order_id,))

    # If a report reason is provided, insert into the reports table
    if reason:
        # Retrieve the seller email from the seller_account table
        cursor.execute('''
            SELECT email FROM seller_account WHERE sellerID = %s
        ''', (seller_id,))
        seller_email = cursor.fetchone()

        if seller_email:
            seller_email = seller_email[0]  # Extract email from the result tuple

            # Insert into the reports table using the seller email
            cursor.execute('''
                INSERT INTO reports (productID, sellerID, buyer, description) 
                VALUES (%s, %s, %s, %s)
            ''', (product_id, seller_email, user_email, reason))

    conn.commit()

    update_order_status(order_id, 'feedback done')

    cursor.close()
    conn.close()

    # Redirect or show a success message
    return redirect('/feedback_success')

 # Adjust this route as needed

@app.route('/feedback_success')
def feedback_success():
    return render_template('feedback_success.html')  # Render the success template


@app.route('/view_feedback/<int:product_id>')
def view_feedback(product_id):
    # Connect to the database and retrieve feedback for the given product_id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # cursor.execute('''
    #     SELECT * FROM feedback 
    #     WHERE product_id = %s
    # ''', (product_id,))
    
    # feedbacks = cursor.fetchall()
    # print("Feedbacks:", feedbacks)

    cursor.execute('SELECT * FROM feedback WHERE product_id = %s', (product_id,))
    feedbacks = cursor.fetchall()

    # Manually mask here
    for f in feedbacks:
        f['user_id'] = mask_email(f['user_id'])

    cursor.close()
    conn.close()

    return render_template('view_feedback.html', feedbacks=feedbacks, product_id=product_id)




@app.route('/orders')
def view_orders():
    # Assuming user_email is stored in session when the user logs in
    user_email = session['user_email']
    orderID = session['orderID']
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all orders for the logged-in user
    cursor.execute('''
        SELECT o.*, o.price, p.prName
        FROM cotbl o
        JOIN producttbl p ON o.product_id = p.productID
        WHERE o.user_id = %s AND o.status IN ("order placed", "order received") AND orderID = %s  
    ''', (user_email, orderID))
    
    user_orders = cursor.fetchall()

    # Convert prPrice to float for each order and remove commas if needed
    for order in user_orders:
        order['price'] = float(order['price'])  # Remove commas and convert to float

    # Close the connection
    cursor.close()
    conn.close()

    # Render the 'view_orders.html' template, passing the fetched orders
    return render_template('view_orders.html', user_orders=user_orders)


#SEARCH BAR
from flask import render_template, request
import sqlite3  # Replace with your database library if different

@app.route('/products')
def products():
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if search_query:
        query = """
        SELECT productID, prType, prName, prPrice, brand 
        FROM producttbl 
        WHERE prName LIKE ? OR brand LIKE ?
        """
        cursor.execute(query, (f'%{search_query}%', f'%{search_query}%'))
    else:
        query = """
        SELECT productID, prType, prName, prPrice, brand 
        FROM producttbl
        """
        cursor.execute(query)
    
    products = cursor.fetchall()
    conn.close()

    # Map the fetched data into dictionaries
    product_list = [
        {
            'productID': row[0],
            'prType': row[1],
            'prName': row[2],
            'prPrice': row[3],
            'brand': row[4]
        }
        for row in products
    ]

    no_products = len(product_list) == 0
    return render_template('buyer_category.html', products=product_list, no_products=no_products)


#BUYER CATEGORY
#showing prType
@app.route('/products/<pr_type>')
def view_prType(pr_type):
        #Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

         #SEARCH
        search_query = request.args.get('search', '').strip()
        query_params = [pr_type]

        query = "SELECT * FROM producttbl WHERE prType = %s AND qty > 0"

        if search_query:
            query += " AND (prName LIKE %s OR brand LIKE %s)"
            search_term = f"%{search_query}%"
            query_params.extend([search_term, search_term])

        cursor.execute(query, tuple(query_params))
        products = cursor.fetchall()


        no_products = len(products) == 0

          # Get distinct categories and brand
        cursor.execute("SELECT DISTINCT category FROM producttbl WHERE prType = %s ", (pr_type,))
        categories = cursor.fetchall()

        cursor.close()
        
        return render_template('buyer_category.html', products=products, pr_type=pr_type, no_products=no_products, 
                               categories=[cat['category'] for cat in categories])
   

#showing categories
@app.route('/products/<pr_type>/<category>')
def view_categories(pr_type, category):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM producttbl WHERE prType = %s AND category = %s AND qty > 0"
        cursor.execute(query, (pr_type, category))
        products = cursor.fetchall()

        no_products = len(products) == 0

         # Get distinct categories and brand
        cursor.execute("SELECT DISTINCT category FROM producttbl WHERE prType = %s", (pr_type,))
        categories = cursor.fetchall()

        return render_template('buyer_category.html', products=products, pr_type=pr_type, category=category, no_products=no_products, 
                               categories=[cat['category'] for cat in categories])

    
#show subcategories
@app.route('/products/<pr_type>/<category>/<subcategory>')
def view_subcategories(pr_type, category, subcategory):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """ SELECT * FROM producttbl 
        WHERE prType = %s AND category = %s AND subcategory = %s AND qty > 0"""

        cursor.execute(query, (pr_type, category, subcategory))
        products = cursor.fetchall()

        no_products = len(products) == 0

          # Get distinct categories and brand
        cursor.execute("SELECT DISTINCT category FROM producttbl WHERE prType = %s", (pr_type,))
        categories = cursor.fetchall()

        return render_template(
            'buyer_category.html', categories=[cat['category'] for cat in categories],
            products = products, no_products=no_products, pr_type=pr_type, category=category, subcategory=subcategory
        )


#product description
@app.route('/product/<product_id>', methods=['GET'])
def product_desc(product_id):
    # Get the buyer's ID from the session
    buyer_id = session.get('buyer_id')
    if not buyer_id:
        flash("Please log in to view product details and messages.", "error")
        return redirect(url_for('login'))

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the product details by productID
    cursor.execute('SELECT * FROM producttbl WHERE productID = %s AND qty > 0', (product_id,))
    get_product = cursor.fetchone()

    # Fetch available sizes for the product
    cursor.execute("SELECT DISTINCT size FROM producttbl WHERE productID = %s AND size IS NOT NULL AND size != ''", (product_id,))
    size = [row['size'] for row in cursor.fetchall()]
    no_size = len(size) == 0

    # Fetch feedback for the given product_id
    cursor.execute('''SELECT * FROM feedback WHERE product_id = %s''', (product_id,))
    feedbacks = cursor.fetchall()

    # Pagination for buyer messages: Default to page 1 with 10 messages per page
    page = int(request.args.get('page', 1))
    messages_per_page = 10
    offset = (page - 1) * messages_per_page

    # Fetch paginated messages for the buyer
    cursor.execute('''
        SELECT m.*, s.name AS seller_name
        FROM messages m
        LEFT JOIN seller_account s ON m.seller_id = s.sellerID
        WHERE m.buyer_id = %s
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s;
    ''', (buyer_id, messages_per_page, offset))
    messages = cursor.fetchall()

    # Get total number of messages for pagination
    cursor.execute('''
        SELECT COUNT(*) FROM messages WHERE buyer_id = %s;
    ''', (buyer_id,))
    total_messages = cursor.fetchone()['COUNT(*)']

    # Close the database connection
    cursor.close()
    conn.close()

    # Calculate the total number of pages for messages
    total_pages = (total_messages + messages_per_page - 1) // messages_per_page

    # Render the template with product details and buyer messages
    if get_product:
        return render_template('productdesc.html',
                               feedbacks=feedbacks,
                               product_id1=product_id,
                               product=get_product,
                               size=size,
                               no_size=no_size,
                               product_id=product_id,
                               messages=messages,
                               total_pages=total_pages,
                               current_page=page,
                                max_qty=get_product['qty'])
    else:
        return "Product not found", 404


@app.route('/send_message', methods=['POST'])
def send_message():
    # Retrieve form data
    seller_id = request.form.get('seller_id')
    buyer_id = session.get('buyer_id')  # Get the buyer ID from the session
    message = request.form.get('message')

    # Ensure all fields are provided
    if not seller_id or not buyer_id or not message:
        return "All fields are required!", 400

    # Save the message to the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO messages (seller_id, buyer_id, message, role)
        VALUES (%s, %s, %s, 'buyer')
        ''',
        (seller_id, buyer_id, message)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(f'/product/{request.referrer.split("/")[-1]}')  # Redirect back to the product page

#FOR LOCATION
def fetch_location_name(code):
    if not code:
        return "Unknown"  # Handle empty or null codes gracefully
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM location_mapping WHERE code = %s", (code,))
        result = cursor.fetchone()
        return result[0] if result else "Unknown"

    except mysql.connector.Error:
        return "Error"  # Handle database errors
    finally:
        cursor.close()
        conn.close()



#PROFILE SETTINGS
@app.route('/profile_setting', methods=['GET', 'POST'])
def profile_setting():
    # Check if the user is logged in
    if 'user_email' not in session:
        flash("Please log in to view your profile.")
        return redirect(url_for('login'))

    user_email = session['user_email']
    
    #Fetch existing address data
    user_data = {'name': '',
                 'number': '',
                 'email': user_email,
                'region': '',
                'province': '',
                'city': '',
                'brgy': '',
                }
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                ba.name,
                ba.mobile_no,
                ba.email,
                addr.region,
                addr.province,
                addr.city,
                addr.brgy
            FROM 
                buyer_account ba
            LEFT JOIN 
                buyer_address addr
            ON 
                ba.address_id = addr.address_id
            WHERE 
                ba.email = %s
        """, (user_email,))
        result = cursor.fetchone()

        if result:
            user_data['name'] = result[0]
            user_data['mobile_no'] = result[1]
            user_data['region'] = result[3] if result[3] else "Unknown"
            user_data['province'] = result[4] if result[4] else "Unknown"
            user_data['city'] = result[5] if result[5] else "Unknown"
            user_data['brgy'] = result[6] if result[6] else "Unknown"


    except mysql.connector.Error as err:
        flash(f"Error fetching address data: {err}")

    finally:
        cursor.close()
        conn.close()

    # If the request is POST, update the address info
    if request.method == "POST":
        region = request.form.get('region_text', request.form.get('region'))
        province = request.form.get('province_text', request.form.get('province'))
        city = request.form.get('city_text', request.form.get('city'))
        barangay = request.form.get('barangay_text', request.form.get('barangay'))

        # Check if the new address information is different from the current
        if region == user_data['region'] and province == user_data['province'] and city == user_data['city'] and barangay == user_data['brgy']:
            flash("Address has not been changed.")

        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE buyer_address 
                    SET region = %s, province = %s, city = %s, brgy = %s 
                    WHERE address_id = (SELECT address_id FROM buyer_account WHERE email = %s)""",
                    (region, province, city, barangay, user_email)
                )
                conn.commit()
                flash("Address updated successfully.")
            except mysql.connector.Error as err:
                flash(f"Error updating address: {err}")
            finally:
                cursor.close()
                conn.close()

        return redirect(url_for('profile_setting'))

    # Fetch order data if GET request
    orders_data = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query for status history
        status_history_query = """
            SELECT status, updated_at FROM status_history
            WHERE orderID = %s
            ORDER BY updated_at ASC
        """

        # SQL queries for different order statuses
        queries = {
            #ORDER PLACED, ORDER APPROVED, ORDER PACKED
            'to_pay_orders': """
                SELECT cotbl.orderID, producttbl.prName, cotbl.quantity, cotbl.price, cotbl.date, cotbl.status, producttbl.prPrice, producttbl.image_paths
                FROM cotbl 
                JOIN producttbl ON cotbl.product_id = producttbl.productID 
                WHERE cotbl.user_id = %s AND cotbl.status IN ('order placed', 'order approved', 'order packed')
            """,

            #ORDER TO SHIP
            'to_ship_orders': """
                SELECT cotbl.orderID, producttbl.prName, cotbl.quantity, cotbl.price, cotbl.date, cotbl.status, producttbl.prPrice, producttbl.image_paths
                FROM cotbl 
                JOIN producttbl ON cotbl.product_id = producttbl.productID 
                WHERE cotbl.user_id = %s AND cotbl.status IN ('order for pick-up', 'order picked-up')
            """,
            #ORDER ON THE WAY
            'to_receive_orders': """
                SELECT cotbl.orderID, producttbl.prName, cotbl.quantity, cotbl.price, cotbl.date, cotbl.status, producttbl.prPrice, producttbl.image_paths
                FROM cotbl 
                JOIN producttbl ON cotbl.product_id = producttbl.productID 
                WHERE cotbl.user_id = %s AND cotbl.status IN ('order on the way', 'order delivered')
            """,
            #ORDER TO RATE
            'to_rate_orders': """
                SELECT cotbl.orderID, producttbl.prName, cotbl.quantity, cotbl.price, cotbl.product_id, cotbl.sellerID, cotbl.orderID, cotbl.received, cotbl.date, producttbl.prPrice, producttbl.image_paths
                FROM cotbl 
                JOIN producttbl ON cotbl.product_id = producttbl.productID 
                WHERE cotbl.user_id = %s AND cotbl.status = 'order received'
            """,
            #COMPLETED
            'completed_orders': """
                SELECT cotbl.orderID, producttbl.prName, cotbl.quantity, cotbl.price, cotbl.date, cotbl.status, producttbl.prPrice, producttbl.image_paths
                FROM cotbl 
                JOIN producttbl ON cotbl.product_id = producttbl.productID 
                WHERE cotbl.user_id = %s AND cotbl.status = 'feedback done'
            """,
        }

         # Execute each query and attach status history
        for key, query in queries.items():
            cursor.execute(query, (user_email,))
            raw_orders = cursor.fetchall()
            enriched_orders = []

            for order in raw_orders:
                cursor.execute(status_history_query, (order['orderID'],))
                history = cursor.fetchall()
                order['status_history'] = history
                enriched_orders.append(order)

            orders_data[key] = enriched_orders

    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('profile_setting.html', user_data=user_data, **orders_data) 



#FOOTER
@app.route('/delivery_footer')
def delivery_footer():
    return render_template('footer/delivery.html')

@app.route('/returns_footer')
def returns_footer():
    return render_template('footer/returns.html')

@app.route('/paymentoption_footer')
def paymentoption_footer():
    return render_template('footer/payment.html')





@app.route('/seller_settings', methods=['GET', 'POST'])
def seller_settings():
    connection = get_db_connection()
    cursor = connection.cursor()
    seller_id = session.get('seller_id')  # Assuming the seller ID is stored in session

    if request.method == 'POST':
        # Get updated values from the form
        name = request.form['name']
        email = request.form['email']
        number = request.form['number']
        password = request.form['password']
        created_at = request.form['created_at']

        # Update the seller's information in the database
        cursor.execute("""
            UPDATE seller_account
            SET name = %s, email = %s, number = %s, password = %s, created_at = %s
            WHERE sellerID = %s
        """, (name, email, number, password, created_at, seller_id))

        connection.commit()
        flash("Profile updated successfully.")

    # Fetch the seller's current information
    cursor.execute("SELECT name, email, number, password, created_at FROM seller_account WHERE sellerID = %s", (seller_id,))
    seller_data = cursor.fetchone()
    
    cursor.close()
    connection.close()

    return render_template('seller/seller_settings.html', seller_data=seller_data)


@app.route('/buyerdashboard/buyer_messages', methods=['GET'])
def buyer_messages():
    buyer_id = session.get('buyer_id')
    if not buyer_id:
        flash("Please log in to access messages.", "error")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Pagination logic: Default to page 1 with 10 messages per page
    page = int(request.args.get('page', 1))
    messages_per_page = 10
    offset = (page - 1) * messages_per_page

    # Fetch paginated messages
    cursor.execute('''
        SELECT m.*, s.name AS seller_name
        FROM messages m
        LEFT JOIN seller_account s ON m.seller_id = s.sellerID
        WHERE m.buyer_id = %s
        ORDER BY m.created_at DESC
        LIMIT %s OFFSET %s;
    ''', (buyer_id, messages_per_page, offset))
    messages = cursor.fetchall()

    # Get total number of messages for pagination
    cursor.execute('''
        SELECT COUNT(*) FROM messages WHERE buyer_id = %s;
    ''', (buyer_id,))
    total_messages = cursor.fetchone()['COUNT(*)']

    cursor.close()
    conn.close()

    # Calculate the total number of pages
    total_pages = (total_messages + messages_per_page - 1) // messages_per_page

    return render_template(
        'buyer_messages.html',
        messages=messages,
        total_pages=total_pages,
        current_page=page
    )







#SELLER PAGE
#SELLER SALES RECORD
@app.route('/seller_salesrecord', methods=['GET'])
def seller_salesrecord():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT sellerID FROM seller_account WHERE email = %s', (session['user_email'],))
    seller = cursor.fetchone()
    
    if not seller:
        # If no seller is found, redirect to login or show an error
        return "Seller not found. Please log in.", 404

    seller_id = seller['sellerID']

    # Get query parameters
    show_all = request.args.get('show_all', 'false') == 'true'
    status_filter = request.args.get('status', '')

    # Fetch total sales, total product, and total orders for the specific seller
    cursor.execute('''
        SELECT 
            SUM(price) AS total_price, 
            SUM(quantity) AS total_quantity, 
            COUNT(*) AS total_rows 
        FROM cotbl 
        WHERE sellerID = %s AND (status = 'feedback done' OR status = 'order received');
    ''', (seller_id,))
    totals = cursor.fetchone()

    # Debug prints to verify the fetched data
    print("Totals:", totals)

    total_sales = f"{totals['total_price'] or 0:,.2f}"
    total_product = totals['total_quantity'] or 0
    total_order = totals['total_rows'] or 0


    cursor.execute('''
        SELECT cotbl.*, producttbl.prName 
        FROM cotbl
        JOIN producttbl ON cotbl.product_id = producttbl.productID
        WHERE cotbl.sellerID = %s AND cotbl.status IN (%s, %s)
    ''', (session['seller_id'], 'order received', 'feedback done'))
    orders = cursor.fetchall()

    status_groups = {
        'order received': [],
        'feedback done': []
    }

    for order in orders:
            status_groups[order['status']].append(order)

    cursor.close()
    conn.close()

    return render_template('seller/seller_salesrecord.html', status_groups=status_groups,
                           total_sales=total_sales,
                            total_product=total_product,
                            total_order=total_order)






@app.route('/seller_feedback')
def seller_feedback():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    sellerID = session['seller_id']
    search_query = request.args.get('search', '').strip()  # Get the search term from query parameters

    # Base query
    query = '''
        SELECT f.user_id, ba.name AS customer_name, p.prName AS product_name, 
               f.feedback, f.created_at
        FROM feedback f
        JOIN buyer_account ba ON f.user_id = ba.email
        JOIN producttbl p ON f.product_id = p.productID 
        WHERE f.sellerID = %s ORDER BY created_at DESC
    '''

    # Add filtering if a search query is provided
    if search_query:
        query += '''
            AND (ba.name LIKE %s OR p.prName LIKE %s OR f.feedback LIKE %s OR f.created_at LIKE %s OR f.user_id LIKE %s)
        '''
        search_param = f"%{search_query}%"
        cursor.execute(query, (sellerID, search_param, search_param, search_param, search_param, search_param))
    else:
        cursor.execute(query, (sellerID,))

    feedback_data = cursor.fetchall()
    cursor.close()
    conn.close()

    # Pass the search query to the template for display
    return render_template('seller/feedbacktest.html', feedback_data=feedback_data, search_query=search_query)


@app.route('/seller_login')
def seller_login():
    return render_template('seller/sellerlogin.html') 

@app.route('/seller_products', methods=['GET'])
def seller_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Update status to "Not Available" where qty is 0 for the current seller
    update_status_query = '''
        UPDATE producttbl 
        SET status = 'Not Available' 
        WHERE sellerID = %s AND qty = 0
    '''
    cursor.execute(update_status_query, (session['seller_id'],))
    conn.commit()

    # Retrieve search query and page number from GET request
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)  # Default to page 1 if not specified
    limit = 10  # Rows per page
    offset = (page - 1) * limit  # Calculate the starting row

    # Base SQL query with LIMIT and OFFSET
    query = '''
        SELECT productID, prName, prPrice, prType, category, subcategory, qty, status
        FROM producttbl WHERE sellerID = %s
    '''
    count_query = 'SELECT COUNT(*) FROM producttbl WHERE sellerID = %s'  # For calculating total pages

    # Add search condition if a search query is present
    if search_query:
        query += '''
            AND (productID LIKE %s OR prName LIKE %s OR prPrice LIKE %s OR
                  prType LIKE %s OR category LIKE %s OR subcategory LIKE %s
                  OR qty LIKE %s OR status LIKE %s)
        '''
        count_query += '''
            AND (productID LIKE %s OR prName LIKE %s OR prPrice LIKE %s OR
                prType LIKE %s OR category LIKE %s OR subcategory LIKE %s OR 
                qty LIKE %s OR status LIKE %s)
        '''
        search_param = f"%{search_query}%"
        params = (session['seller_id'],) + (search_param,) * 8
    else:
        params = (session['seller_id'],)

    # Execute count query to get total rows
    cursor.execute(count_query, params)
    total_rows = cursor.fetchone()['COUNT(*)']

    # Execute main query to fetch product data
    cursor.execute(query + ' ORDER BY productID ASC LIMIT %s OFFSET %s', params + (limit, offset))
    product_data = cursor.fetchall()

    # Calculate total pages (rounded up)
    total_pages = (total_rows + limit - 1) // limit

    cursor.close()
    conn.close()

    # Pass data to the template
    return render_template(
        'seller/seller_products.html',
        product_data=product_data,
        search_query=search_query,
        page=page,
        total_pages=total_pages
    )


#SELLER LOGIN
@app.route('/slogin_submit', methods=['POST'])
def slogin_submit():
    email = request.form['email']
    password = request.form['password']

    #Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM seller_account WHERE email = %s", (email,))
    user = cursor.fetchone() 

    
    if user:
        if user['password'] == password:
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['seller_id'] = user['sellerID']
            cursor.close()
            conn.close()
            return redirect(url_for('sellerdashboard'))
        
        
        else:
            flash('Incorrect password. Please try again.', "error")
            return redirect(url_for('seller_login'))
    else:
        flash('Email not found. Please check your email or password.', "error")
        return redirect(url_for('seller_login'))
        
    



# Email sending function
def send_email(recipient, subject, body, sender):
    msg = Message(subject, recipients=[recipient], body=body, sender=sender)
    try:
        mail.send(msg)
        print(f"Email sent successfully to {recipient} from {sender}.")
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")



#RIDER ASSIGN
@app.route('/assign_rider', methods=['POST'])
def assign_rider():
    order_id = request.form.get('order_id')
    rider_email = request.form.get('rider_email')

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Assign the rider to the order
    cursor.execute('''
        UPDATE cotbl
        SET rider_email = %s
        WHERE orderID = %s
    ''', (rider_email, order_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Rider assigned successfully.')
    return redirect(url_for('seller_order'))  # Adjust if different



@app.route('/seller_order', methods=['GET', 'POST'])
def seller_order():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch orders based on status for the logged-in seller
    cursor.execute('''
        SELECT cotbl.*, producttbl.prName, buyer_account.name AS buyer_name, 
               buyer_address.region, buyer_address.province, buyer_address.city, 
               buyer_address.brgy
        FROM cotbl
        JOIN producttbl ON cotbl.product_id = producttbl.productID
        JOIN buyer_account ON cotbl.user_id = buyer_account.email
        LEFT JOIN buyer_address ON buyer_account.address_id = buyer_address.address_id
        WHERE cotbl.sellerID = %s AND cotbl.status IN (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (session['seller_id'], 'order placed', 'order approved', 'order on the way', 'order received', 'feedback done', 'order packed', 'order for pick-up', 'order picked-up'))
    orders = cursor.fetchall()

    # Initialize groups
    status_groups = {
        'order placed': [],
        'order approved': [],
        'order packed': [],
        'order for pick-up': [],
        'order picked-up': [],
        'order on the way': [],
        'order received': [],
        'feedback done': []
    }

    # For each order, fetch riders in the buyer's province (only if needed)
    # For each order, fetch riders in the buyer's province (for order packed and order for pick-up)
    for order in orders:
        if order['status'] in ['order packed', 'order for pick-up']:
            cursor.execute("""
                SELECT ra.*, addr.*
                FROM rider_account ra
                JOIN rider_address addr ON ra.address_id = addr.address_id
                WHERE ra.status = "Approved"
                AND addr.city = %s AND addr.province = %s
            """, (order['city'], order['province']))
            order['matching_riders'] = cursor.fetchall()
        else:
            order['riders'] = []  # no riders for other statuses

        status_groups[order['status']].append(order)


    # Handle order status update form submission
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        current_status = request.form.get('current_status')
        datenow = datetime.now()  

        # Determine and update new status based on current status
        if current_status == 'order approved':
            new_status = 'order packed'
            cursor.execute('UPDATE cotbl SET status = %s, shipped = %s WHERE id = %s', (new_status,datenow, order_id))
            conn.commit()
            update_order_status(order_id, new_status)
        elif current_status == 'order packed':
            new_status = 'order for pick-up'
            cursor.execute('UPDATE cotbl SET status = %s, approved = %s WHERE id = %s', (new_status,datenow, order_id))
            conn.commit()
            update_order_status(order_id, new_status)
        elif current_status == 'order for pick-up':
            new_status = 'order picked-up'
            cursor.execute('UPDATE cotbl SET status = %s, approved = %s WHERE id = %s', (new_status,datenow, order_id))
            conn.commit()
            update_order_status(order_id, new_status)
        elif current_status == 'order placed':
            new_status = 'order approved'
            cursor.execute('UPDATE cotbl SET status = %s, approved = %s WHERE id = %s', (new_status,datenow, order_id))
            conn.commit()
            update_order_status(order_id, new_status)
        else:
            new_status = None

        if new_status:
            cursor.execute('SELECT * FROM cotbl JOIN producttbl ON cotbl.product_id = producttbl.productID WHERE cotbl.orderID = %s', (order_id,))
            order_details = cursor.fetchone()
            userType = "buyer"
            userActID = order_details['user_id']
            userActivity = f"Seller successfully updated order of buyer {userActID} status to {new_status}"
            insert_user_log(userActID, userType, userActivity)

            if order_details:
                buyer_email = order_details['user_id']
                product_name = order_details['prName']
                seller_email = session['user_email']

                subject = f"Order Status Update for {product_name}"
                body = f"Dear Buyer,\n\nYour order for '{product_name}' has been updated to '{new_status}'.\n\nBest regards,\n{seller_email}"

                send_email(recipient=buyer_email, subject=subject, body=body, sender=seller_email)

        return redirect(url_for('seller_order'))

    cursor.close()
    conn.close()

    return render_template('seller/seller_order.html', status_groups=status_groups)

@app.route('/disapprove_order', methods=['POST'])
def disapprove_order():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Retrieve form data
    order_id = request.form.get('order_id')
    current_status = request.form.get('current_status')
    reason = request.form.get('reason')  # Get the reason for disapproval

    # Set the new status to 'order disapproved'
    if current_status in ['order placed']:
        new_status = 'order rejected'

        # Update the order status in the database
        cursor.execute('UPDATE cotbl SET status = %s WHERE id = %s', (new_status, order_id))
        conn.commit()
        

        # Get buyer email and order details for email sending
        cursor.execute('SELECT * FROM cotbl JOIN producttbl ON cotbl.product_id = producttbl.productID WHERE cotbl.id = %s', (order_id,))
        order_details = cursor.fetchone()

        if order_details:
            # Get the product details using product_id from order_details
            cursor.execute('SELECT * FROM producttbl WHERE productID = %s', (order_details['product_id'],))
            update = cursor.fetchone()
            tblqty = update['qty']
            # Retrieve quantity from the order details
            qty = order_details['quantity']
            pID = update['productID']
            if tblqty == 0:
                cursor.execute('UPDATE producttbl SET qty = qty + %s , status = "Available" WHERE productID = %s', (qty, pID))
                print(f"Updated producttbl: Return quantity for productID {pID} by {qty} status updated")
            else:
            # Update the quantity in the product table
                cursor.execute('UPDATE producttbl SET qty = qty + %s WHERE productID = %s', (qty, pID))
                print(f"Updated producttbl: Return quantity for productID {pID} by {qty}")
            
            conn.commit()
        if order_details:
            buyer_email = order_details['user_id']
            product_name = order_details['prName']
            seller_email = session['user_email']
            
            # Email subject and body with reason
            subject = f"Order Status Update for {product_name}"
            body = f"Dear Buyer,\n\nYour order for '{product_name}' has been disapproved.\n\nReason for disapproval: {reason}\n\nBest regards,\n{seller_email}"

            # Send email
            send_email(recipient=buyer_email, subject=subject, body=body, sender=seller_email)
            print("email send")
        # Redirect back to the seller order page after disapproval
        return redirect(url_for('seller_order'))

    # Close the database connection
    cursor.close()
    conn.close()

    return redirect(url_for('seller_order'))    





#Route for the registration page
@app.route('/seller_register')
def seller_register():
    return render_template('seller/sellerregister.html')

#SELLER registration
#Route to handle form submission
@app.route('/sregister_submit', methods=['POST'])
def sregister_submit():
    name = request.form['name']
    dateofbirth = request.form['dateofbirth']
    email = request.form['email']
    number = request.form['number']
    gender = request.form.get('gender')
    password = request.form['password']
    confirmpassword = request.form['confirmpassword']
    region = request.form.get('region_text', request.form.get('region'))
    province = request.form.get('province_text', request.form.get('province'))
    city = request.form.get('city_text', request.form.get('city'))
    barangay = request.form.get('barangay_text', request.form.get('barangay'))
    validID = request.files['validID']

    if not gender:
            flash('Please select a gender.', 'error')
            return render_template('seller/sellerregister.html', form=request.form)
      # Validate date of birth and age
    try:
        dob = datetime.strptime(dateofbirth, '%Y-%m-%d')
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            flash('You must be at least 18 years old to register.', 'error')
            return render_template('seller/sellerregister.html', form=request.form)
    except ValueError:
        flash('Invalid date of birth format. Please use YYYY-MM-DD.', 'error')
        return render_template('seller/sellerregister.html', form=request.form)
    

      #Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    #Check if the email already exists
    cursor.execute("SELECT * FROM seller_account WHERE email = %s", (email,))
    existing_user = cursor.fetchone()

    if existing_user:
        flash('This email is already registered. Please use a different email.', "error")
        return render_template('seller/sellerregister.html', form=request.form)

    #confirm pass
    if confirmpassword != password:
        flash('Password does not match. Please try again.', "error")
        return render_template('seller/sellerregister.html', form=request.form)
    #mobile number
    if not number.isdigit() or len(number) != 11:
        flash('Please enter a valid mobile number')
        return render_template('seller/sellerregister.html', form=request.form)
    #password requiremtns
    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$'
    if not re.match(password_regex, password):
        flash('Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, and a number.', 'error')
        return render_template('seller/sellerregister.html', form=request.form)

   # Save valid ID file
    if validID and allowed_file(validID.filename):  # Ensure valid file extension
        image_path = f'static/assets/IDs/{secure_filename(validID.filename)}'
        validID.save(image_path)
    else:
        flash('Invalid ID upload. Only images are allowed.', 'error')
        return render_template('reg.html', form=request.form)

    try:
        #Insert form data into the database
        cursor.execute("""INSERT INTO seller_account (name, dateofbirth, email, number, gender, password, image_path, status) VALUES (%s, %s, %s, %s, %s, %s, %s, "Pending")""",
                      (name, dateofbirth, email, number, gender, password, image_path))
        conn.commit()
       
        seller_id = cursor.lastrowid

        cursor.execute("""INSERT INTO seller_address (region, province, city, brgy, seller_id) VALUES (%s, %s, %s, %s, %s) """, 
                       (region, province, city, barangay, seller_id))
        conn.commit()

        address_id = cursor.lastrowid

        cursor.execute("UPDATE seller_account SET address_id = %s WHERE sellerID = %s", (address_id, seller_id))
        conn.commit()

        flash('Registration successful! Your account is pending approval.')
        return redirect(url_for('seller_register'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return render_template('seller/sellerregister.html')
    

#FORGOT PASSWORD SELLER


#SELLER DASHBOARD
@app.route('/sellerdashboard')
def sellerdashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Retrieve sellerID using session['user_email']
    cursor.execute('SELECT sellerID FROM seller_account WHERE email = %s', (session['user_email'],))
    seller = cursor.fetchone()
    
    if not seller:
        # If no seller is found, redirect to login or show an error
        return "Seller not found. Please log in.", 404

    seller_id = seller['sellerID']

    # Get query parameters
    show_all = request.args.get('show_all', 'false') == 'true'
    status_filter = request.args.get('status', '')

    # Fetch total sales, total product, and total orders for the specific seller
    cursor.execute('''
        SELECT 
            SUM(price) AS total_price, 
            SUM(quantity) AS total_quantity, 
            COUNT(*) AS total_rows 
        FROM cotbl 
        WHERE sellerID = %s AND (status = 'feedback done' OR status = 'order received');
    ''', (seller_id,))
    totals = cursor.fetchone()

    # Debug prints to verify the fetched data
    print("Totals:", totals)

    total_sales = f"{totals['total_price'] or 0:,.2f}"
    total_product = totals['total_quantity'] or 0
    total_order = totals['total_rows'] or 0

    # Base query for fetching orders
    query = '''
        SELECT user_id, quantity, price, status
        FROM cotbl
        WHERE sellerID = %s
    '''
    params = (seller_id,)

    # Filtering by status if status_filter is provided
    if status_filter:
        query += ' AND status = %s'
        params += (status_filter,)

    # Limiting to recent orders if "Show All" is not triggered
    if not show_all:
        query += ' ORDER BY quantity DESC LIMIT 5'
    else:
        query += ' ORDER BY quantity DESC'

    cursor.execute(query, params)
    orders = cursor.fetchall()

    # Debug prints for orders
    print("Orders:", orders)

    # Close the database connection
    cursor.close()
    conn.close()

    # Pass the totals, orders, and current filter status to the template
    return render_template(
        'seller/seller.html',
        total_sales=total_sales,
        total_product=total_product,
        total_order=total_order,
        orders=orders,
        status_filter=status_filter,
        show_all=show_all
    )



# @app.route('/sellerdashboard/seller_messages', methods=['GET'])
# def seller_messages():
#     seller_id = session.get('seller_id')  # Ensure the seller is logged in

#     if not seller_id:
#         flash("Please log in to access messages.", "error")
#         return redirect(url_for('login'))

#     conn = get_db_connection()
#     cursor = conn.cursor(dictionary=True)

#     # Fetch messages for the seller
#     cursor.execute('''
#         SELECT m.*, 
#                b.name AS buyer_name
#         FROM messages m
#         LEFT JOIN buyer_account b ON m.buyer_id = b.id_no
#         WHERE m.seller_id = %s
#         ORDER BY m.created_at DESC;
#     ''', (seller_id,))
#     messages = cursor.fetchall()

#     cursor.close()
#     conn.close()

#     return render_template('seller/seller_messages.html', messages=messages)


@app.route('/sellerdashboard/seller_messages', defaults={'buyer_id': None}, methods=['GET'])
@app.route('/sellerdashboard/seller_messages/<int:buyer_id>', methods=['GET'])
def seller_messages(buyer_id):
    seller_id = session.get('seller_id')

    if not seller_id:
        flash("Please log in to access messages.", "error")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all unique buyers who messaged the seller
    cursor.execute('''
        SELECT DISTINCT m.buyer_id, b.name AS buyer_name
        FROM messages m
        LEFT JOIN buyer_account b ON m.buyer_id = b.id_no
        WHERE m.seller_id = %s;
    ''', (seller_id,))
    buyers = cursor.fetchall()

    messages = []
    selected_buyer = None

    # If a buyer is selected, get the conversation
    if buyer_id:
        cursor.execute('''
            SELECT m.*, b.name AS buyer_name
            FROM messages m
            LEFT JOIN buyer_account b ON m.buyer_id = b.id_no
            WHERE m.seller_id = %s AND m.buyer_id = %s
            ORDER BY m.created_at ASC;
        ''', (seller_id, buyer_id))
        messages = cursor.fetchall()
        selected_buyer = buyer_id

    cursor.close()
    conn.close()

    return render_template(
        'seller/seller_messages.html',
        buyers=buyers,
        messages=messages,
        selected_buyer=selected_buyer
    )



@app.route('/sellerdashboard/send_message', methods=['POST'])
def send_messages():
    seller_id = session.get('seller_id')  # Ensure the seller is logged in

    if not seller_id:
        flash("Please log in to send messages.", "error")
        return redirect(url_for('login'))

    # Get form data
    buyer_id = request.form['buyer_id']
    message_content = request.form['message']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert message into the database
    cursor.execute('''
        INSERT INTO messages (seller_id, buyer_id, message, created_at, role)
        VALUES (%s, %s, %s, NOW(), 'seller');
    ''', (seller_id, buyer_id, message_content))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Message sent successfully!", "success")
    return redirect(url_for('seller_messages'))


@app.route('/seller_report')
def seller_report():
    return render_template('seller/seller_report.html')


#ADD PRODUCT
UPLOAD_FOLDER = 'static/assets/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16*1024*1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/addprd')
def addprd():
    return render_template('seller/seller_addproduct.html')

#seller add product
@app.route('/addprd_submit', methods=['POST'])
def addprd_submit():

    prName = request.form['prdname-input']
    prDesc = request.form['desc-input']
    size = request.form['size-input']
    color = request.form['color-input']
    prPrice = float(request.form['price-input'].replace(',', ''))
    status = "Available"
    brand = request.form['brand-input']
    prType = request.form['type'] 
    category = request.form['category'] 
    subcategory = request.form['subcategory']
    qty = request.form['qty-input']
    sellerID =  session.get('seller_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    #check if product exists
    cursor.execute("SELECT * FROM producttbl WHERE prName = %s AND color = %s AND size = %s", (prName, color, size,))
    existing_prd = cursor.fetchone()

    if existing_prd:
        flash('The product already exists.')
        return redirect(url_for('addprd'))
    
    # Generate a new productID
    cursor.execute("SELECT MAX(productID) FROM producttbl")
    max_product_id = cursor.fetchone()[0]
    new_productID = (max_product_id or 0) + 1

    #computing discount percentage
    #discounted_price = float(prPrice * (1 - (discount_prcnt / 100)).replace(',', ''))
    
    
    # Create the upload directory path based on type and category
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], prType, category)
    os.makedirs(upload_dir, exist_ok=True)

    #if img file is not uploaded
    if 'files[]' not in request.files:
        flash('No file part')
        return redirect(url_for('addprd'))
    
    files = request.files.getlist('files[]')
    file_paths = []

    for file in files:
        if file.filename == '':
            flash('Four images should be selected for uploading')
            return redirect(url_for('addprd'))
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            file_paths.append(file_path)  # Store the path of the saved file
        else:
            flash('Publish was unsuccessful! Allowed image type is only .png')
            return redirect(url_for('addprd'))
    
    if not file_paths:
        flash('No images uploaded successfully.')
        return redirect(url_for('addprd'))
    
    # Concatenate file paths into a single string
    image_paths = json.dumps(file_paths)



    sql = """INSERT INTO producttbl (productID, prName, prDesc, size, color, prPrice, status, brand, prType, category, subcategory, qty, image_paths, sellerID) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,  %s, %s)"""
    values = (new_productID, prName, prDesc, size, color, prPrice, status, brand, prType, category, subcategory, qty, file_path, sellerID) #discounted_price, discount_prcnt)

    cursor.execute(sql, values)
    conn.commit()  
    cursor.close()
    conn.close()

    flash('Product added successfully')
    return render_template('seller/seller_addproduct.html')

#display image
@app.route('/display/<filename>')
def display_image(filename):                       
    print(filename)
    return redirect(url_for('static', filename='assets/' + filename), code=301)

#SELLER EDIT PRODUCTS
@app.route('/editproducts', methods=['GET'])
def editproducts():
    product_id = request.args.get('product_id')  # Get product ID from query string
    if not product_id:
        return "Product ID is missing.", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM producttbl WHERE productID = %s", (product_id,))
    product = cursor.fetchone()
    # Parse `image_paths` if it's a JSON string or comma-separated
    image_paths = product.get('image_paths', None)
    if image_paths:
        image_paths = image_paths.split(',')  # Example for comma-separated values
        # For JSON string: image_paths = json.loads(image_paths)

    cursor.close()
    conn.close()

    if not product:
            return "Product not found.", 404
    
    
    return render_template('seller/seller_editproduct.html', product=product, image_paths=image_paths)


@app.route('/editproducts', methods=['POST'])
def edit_product_submit():
    product_id = request.form.get('product_id')

    if not product_id:
        flash('Product ID is missing.')
        return redirect(url_for('seller_products'))

    # Retrieve other form data
    prName = request.form.get('prdname-input')
    prDesc = request.form['desc-input']
    size = request.form['size-input']
    color = request.form['color-input']
    prPrice = float(request.form['price-input'].replace(',', ''))
    status = "Available"
    brand = request.form['brand-input']
    prType = request.form['type'] 
    category = request.form['category'] 
    subcategory = request.form['subcategory']
    qty = request.form['qty-input']


    # Save updated paths to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch existing image paths from the database
    cursor.execute("SELECT image_paths FROM producttbl WHERE productID = %s", (product_id,))
    product = cursor.fetchone()

    if not product:
        flash('Product not found.')
        return redirect(url_for('editproducts', product_id=product_id))

    existing_image_paths = product['image_paths']
    
    if existing_image_paths:
        try:
            image_paths_list = json.loads(existing_image_paths)
        except json.JSONDecodeError:
            image_paths_list = []
    else:
        image_paths_list = []


    # Check if new files are uploaded
    files = request.files.getlist('files[]')
    if files and any(file.filename for file in files):
        # Handle file upload
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], prType, category)
        os.makedirs(upload_dir, exist_ok=True)

        new_file_paths = []
        for file in files:
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                new_file_paths.append(file_path)
            elif file.filename:
                flash('Allowed image type is only .png')
                return redirect(url_for('editproducts', product_id=product_id))

        # Replace the existing image paths with the new ones
        image_paths_list = new_file_paths

    # Convert the list of paths to a JSON string
    image_paths = json.dumps(image_paths_list)


    try:
        cursor.execute("""
            UPDATE producttbl
            SET prName = %s, prDesc = %s, size = %s, color = %s, prPrice= %s, status = %s, 
                    brand=%s, prType=%s, category=%s, subcategory=%s, qty=%s, image_paths = %s
            WHERE productID = %s
        """, (prName,  prDesc, size, color, prPrice, status, brand, prType, category, subcategory, qty, image_paths, product_id))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Product updated successfully')
        return redirect(url_for('editproducts', product_id=product_id))
    
    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

#DELETE PRODUCTS
@app.route('/delete_product', methods=['POST'])
def delete_product():

    product_id = request.form['product_id']

    if not product_id:
        flash('Product ID is missing.')
        return redirect(url_for('seller_products'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute('DELETE FROM producttbl WHERE productID = %s', (product_id,))
        conn.commit()
        flash('Product deleted successfully.')

    except mysql.connector.Error as err:
        flash(f"Database error: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('seller_products'))

#ADMIN PAGE
@app.route('/adminreports')
def adminreports():
    return render_template('admin/adminreports.html')







# ---------------API FOR MOBILE APP FLUTTER------------------------



#-------LOGIN API
@app.route('/api/login', methods=['POST'])
def login_api():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM buyer_account WHERE email = %s COLLATE utf8mb4_bin AND password = %s COLLATE utf8mb4_bin",
            (email, password)
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            session['user_email'] = user['email']

            return jsonify({'success': True, 'user': user})

        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print('Error:', str(e))
        return jsonify({'success': False, 'message': 'Server error occurred'}), 500


@app.route('/api/location-name', methods=['GET'])
def get_location_name():
    code = request.args.get('code')  # e.g., /api/location-name?code=123

    if not code:
        return jsonify({'name': 'Unknown'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM location_mapping WHERE code = %s", (code,))
        result = cursor.fetchone()
        return jsonify({'name': result[0] if result else 'Unknown'})
    except mysql.connector.Error:
        return jsonify({'name': 'Error'}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/register', methods=['POST'])
def register_api():
    try:
        data = request.get_json()

        name = data.get('name')
        gender = data.get('gender')
        birthday = data.get('birthday')
        phone = data.get('phone')
        region = data.get('region')
        province = data.get('province')
        city = data.get('city')
        barangay = data.get('barangay')
        street = data.get('street')
        email = data.get('email')
        password = data.get('password')
        confirmpassword = data.get('confirmpassword', password)  # Default to password if not sent

        print("Starting registration...")
        print("User data received:", data)
        print("Passed validation")

        # image = request.files.get('image')
        # image_path = None

        # if image and allowed_file(image.filename):
        #     filename = secure_filename(image.filename)
        #     image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #     image.save(image_path)

        
        if not all([name, gender, birthday, phone, region, province, city, barangay, email, password]):
            return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

        if password != confirmpassword:
            return jsonify({'status': 'error', 'message': 'Password does not match'}), 400

        password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$'
        if not re.match(password_regex, password):
            return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, and a number.'}), 400

        image_path = ''  # No image
        street = street if street.strip() else None

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM buyer_account WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({'status': 'error', 'message': 'Email already registered'}), 400

        try:
            cursor.execute("""
                INSERT INTO buyer_account 
                (name, gender, dateofbirth, mobile_no, email, password, image_path, status, address_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending', 0)
            """, (name, gender, birthday, phone, email, password, image_path))
            print("Buyer account inserted.")
        except Exception as e:
            print("Error inserting buyer_account:", e)
            return jsonify({'status': 'error', 'message': str(e)}), 400


        db.commit()
        buyer_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO buyer_address (region, province, city, brgy, street, buyer_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (region, province, city, barangay, street, buyer_id))
        db.commit()
        address_id = cursor.lastrowid

        cursor.execute("UPDATE buyer_account SET address_id = %s WHERE id_no = %s", (address_id, buyer_id))
        db.commit()
        print("Inserted buyer_account with ID:", buyer_id)
        cursor.close()
        db.close()

        return jsonify({'status': 'success', 'message': 'Registration successful'}), 200

    except Exception as e:
        print("Registration error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500


otp_store = {}  # { email: otp }

def generate_otp():
    return str(random.randint(100000, 999999))

@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    otp = generate_otp()
    otp_store[email] = otp  # Save OTP temporarily

    msg = Message("Your Athletyc OTP Code",
                  sender="valdellon44@gmail.com",
                  recipients=[email])
    msg.body = f"Hello, Your 2-Step Verification code for {email} is: {otp}. \n\nEnter the above code into the 2-Step Verification screen to finish logging in. \n\nIMPORTANT: Do not share your security codes with anyone. Athletyc will never ask for your codes. By sharing your security codes with someone else, you are putting your account and its content at high risk. \n\nThank You, \n\nThe Athletyc Team"
    mail.send(msg)

    return jsonify({'message': 'OTP sent successfully'}), 200

@app.route('/api/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    if otp_store.get(email) == otp:
        del otp_store[email]  # Invalidate OTP after use

         # Fetch user info from DB by email
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM buyer_account WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            return jsonify({'message': 'OTP verified', 'user': user}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    else:
        return jsonify({'error': 'Invalid OTP'}), 400
    

#FORGOT PASSWORD
@app.route('/api/forgot_password', methods=['POST'])
def api_forgot_password():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM buyer_account WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        send_reset_email(email)
        return jsonify({'message': 'A password reset email has been sent.'}), 200
    else:
        return jsonify({'error': 'Email not found'}), 404


def api_send_reset_email(email):
    try:
        token = secrets.token_urlsafe(32)  # Generate a secure token
        tokens_store[token] = email
        reset_link = f"myapp://reset_password/{token}"
        
        msg = Message("Password Reset Request",
                      sender="noreply@example.com",
                      recipients=[email])
        msg.body = f"Please use the following link to reset your password: {reset_link}"
        mail.send(msg)
    except Exception as e:
        print(f"Email sending failed: {e}")


tokens_store = {}  # Temporary storage. In production, use a DB with expiry.

@app.route('/api/reset_password/<token>', methods=['POST'])
def api_reset_password(token):
    data = request.get_json()
    new_password = data.get('new_password')

    if not new_password:
        return jsonify({'error': 'New password is required'}), 400

    email = tokens_store.get(token)
    if not email:
        return jsonify({'error': 'Invalid or expired token'}), 400

    # Update the user's password (hashed in production)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE buyer_account SET password = %s WHERE email = %s", (new_password, email))
    conn.commit()
    cursor.close()
    conn.close()

    # Optionally remove token
    del tokens_store[token]

    return jsonify({'message': 'Password reset successful'}), 200




#SHOW PRODUCTS 
@app.route('/api/products', methods=['GET'])
def get_products():
    pr_type = request.args.get('prType')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM producttbl WHERE prType = %s", (pr_type,))
    products = cursor.fetchall()

    cursor.close()
    conn.close()
    return jsonify(products)



#SHOW HOMEPAGE BY CATEGORIES
@app.route('/api/products/by_type/<pr_type>', methods=['GET'])
def api_get_products_by_type(pr_type):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM producttbl WHERE prType = %s", (pr_type,))
        products = cursor.fetchall()
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()


#SHOW PROFILE/ACCOUNT DETAILS
@app.route('/api/profile', methods=['POST'])
def get_profile():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Missing email'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
            SELECT 
                ba.name,
                ba.mobile_no,
                ba.email,
                addr.region,
                addr.province,
                addr.city,
                addr.brgy,
                addr.street
            FROM 
                buyer_account ba
            LEFT JOIN 
                buyer_address addr
            ON 
                ba.address_id = addr.address_id
            WHERE 
                ba.email = %s
        """, (email,))
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return jsonify(user)
    else:
        return jsonify({'error': 'User not found'}), 404



#IN PROFILE ACCOUNT, EDIT ADDRESS
@app.route('/api/update_address', methods=['POST'])
def update_address():
    data = request.json
    print("Received address data:", data)

    email = data.get('email')
    street = data.get('street', '').strip()
    region_name = data.get('region')
    province_name = data.get('province')
    city_name = data.get('city')
    brgy_name = data.get('brgy')

    if not all([email, region_name, province_name, city_name, brgy_name]):
        return jsonify({'status': 'error', 'message': 'Invalid or incomplete address data.'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT address_id FROM buyer_account WHERE email = %s", (email,))
        result = cursor.fetchone()
        print("Address ID lookup result:", result)

        if result and result['address_id']:
            address_id = result['address_id']
            cursor.execute("""
                UPDATE buyer_address 
                SET region = %s, province = %s, city = %s, brgy = %s, street = %s
                WHERE address_id = %s
            """, (region_name, province_name, city_name, brgy_name, street, address_id))
            print(f"Updated {cursor.rowcount} rows")
        else:
            cursor.execute("""
                INSERT INTO buyer_address (region, province, city, brgy, street) 
                VALUES (%s, %s, %s, %s, %s)
            """, (region_name, province_name, city_name, brgy_name, street))
            new_id = cursor.lastrowid
            cursor.execute("UPDATE buyer_account SET address_id = %s WHERE email = %s", (new_id, email))
            print(f"Inserted new address ID: {new_id}")

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print(f"Exception occurred: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500





#SHOW PRODUCTS FROM CART API
@app.route('/api/show_cart', methods=['GET'])
def show_cartprd():
    email = request.args.get('email')  # GET param like /api/show_cart?email=test@gmail.com

    if not email:
        return jsonify({'success': False, 'message': 'Missing email'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('''
    SELECT p.*, c.quantity, c.total_price
    FROM producttbl p
    JOIN carttbl c ON p.productID = c.product_id
    WHERE c.user_id = %s''', (email,))
    
    cart_products = cursor.fetchall()

    if not cart_products:
        print("Cart is empty for user:", email)
        cursor.close()
        conn.close()
        return jsonify([])

    for product in cart_products:
        # Handle comma if price is a string with commas, e.g., '1,000.00'
        if isinstance(product['prPrice'], str):
            product['prPrice'] = float(product['prPrice'].replace(',', ''))
        else:
            product['prPrice'] = float(product['prPrice'])

    cursor.close()
    conn.close()
    return jsonify(cart_products)


#DELETE ITEM FROM CART API
@app.route('/api/delete_from_cart', methods=['POST'])
def delete_from_cart_api():
    data = request.get_json()
    email = data.get('email')
    product_id = data.get('product_id')

    if not email or not product_id:
        return jsonify({'success': False, 'message': 'Missing data'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM carttbl WHERE user_id = %s AND product_id = %s', (email, product_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'success': True})


#ADD TO CART API 
@app.route('/api/add_to_cart', methods=['POST'])
def add_to_cart_api():
    data = request.get_json()

    email = data.get('email')  # No session use
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    if not email or not product_id:
        return jsonify({'success': False, 'message': 'Missing email or product ID'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get product details
        cursor.execute('SELECT prPrice, qty, sellerID FROM producttbl WHERE productID = %s', (product_id,))
        product = cursor.fetchone()

        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404

        price = float(str(product[0]).replace(",", ""))
        current_qty = product[1]
        sellerID = product[2]

        if current_qty < quantity:
            return jsonify({'success': False, 'message': 'Not enough stock available'}), 400

        total_price = round(price * quantity, 2)

        # Check if already in cart
        cursor.execute('SELECT id FROM carttbl WHERE user_id = %s AND product_id = %s', (email, product_id))
        existing_item = cursor.fetchone()

        if existing_item:
            cursor.execute(
                'UPDATE carttbl SET quantity = quantity + %s, total_price = total_price + %s WHERE id = %s',
                (quantity, total_price, existing_item[0])
            )
        else:
            cursor.execute(
                'INSERT INTO carttbl (user_id, product_id, quantity, total_price, sellerID) VALUES (%s, %s, %s, %s, %s)',
                (email, product_id, quantity, total_price, sellerID)
            )

        # Update stock
        #cursor.execute('UPDATE producttbl SET qty = qty - %s WHERE productID = %s', (quantity, product_id))
        conn.commit()

        # Return updated cart count
        cursor.execute('SELECT COUNT(product_id) FROM carttbl WHERE user_id = %s', (email,))
        cart_count = cursor.fetchone()[0] or 0

        return jsonify({'success': True, 'message': 'Added to cart successfully', 'cart_count': cart_count}), 200

    except Exception as e:
        conn.rollback()
        print('Add to cart error:', str(e))
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()






# #REDUCE STOCK FROM ADDING TO CART
# @app.route('/api/reduce_stock', methods=['POST'])
# def reduce_stock():
#     product_id = request.form.get('productID')
#     quantity = int(request.form.get('qty', 1))

#     conn = get_db_connection()
#     cursor = conn.cursor()

#     # Optional: check current stock first
#     cursor.execute("SELECT qty FROM producttbl WHERE id = %s", (product_id,))
#     stock = cursor.fetchone()
#     if stock and stock[0] >= quantity:
#         cursor.execute(
#             "UPDATE producttbl SET qty = qty - %s WHERE id = %s",
#             (quantity, product_id)
#         )
#         conn.commit()
#         return jsonify({'status': 'success'})
#     else:
#         return jsonify({'status': 'failed', 'message': 'Insufficient stock'}), 400



#APPLY VOUCHER ON CHECKOUT PAGE API
@app.route('/api/apply-voucher', methods=['POST'])
def apply_voucher():
    try:
        data = request.get_json()
        code = data.get('code')
        total_price = data.get('totalPrice')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vouchers WHERE code = %s", (code,))
        voucher = cursor.fetchone()

        if not voucher:
            return jsonify({'success': False, 'message': 'Voucher is not found'}), 200

        if datetime.now().date() > voucher['expiration_date']:
            return jsonify({'success': False, 'message': 'Voucher has expired'}), 200

        if float(total_price) < voucher['min_spend']:
            return jsonify({'success': False, 'message': 'Minimum amount not met'}), 200

        if voucher['code_limit'] <= 0:
            return jsonify({'success': False, 'message': 'Voucher usage limit reached'}), 200

        # All good: reduce usage and return discount
        cursor.execute("UPDATE vouchers SET code_limit = code_limit - 1 WHERE code = %s", (code,))
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Voucher applied successfully',
            'discount_amount': float(voucher['discount_amount'])
        }), 200

    except Exception as e:
        print("Error in apply_voucher:", str(e))  # Print to Flask console
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


import string

#SUCCESSFULLY PLACED AN ORDER, CHECKED OUT
@app.route('/api/place-order', methods=['POST'])
def place_order():
    try:
        data = request.get_json()
        print("Incoming order payload:", data)
        print("Received data:", data)
        if not data:
            return jsonify({'success': False, 'message': 'Invalid or missing JSON body'})
        
        user_email = data['email']
        items = data['items']  # List of dicts with product_id, quantity, price, sellerID
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Generate an orderID
        orderID = int(''.join(random.choices(string.digits, k=8)))


        for item in items:
            product_id = item['product_id']
            quantity = int(item['quantity'])
            price = float(item['price'])
            sellerID = item['sellerID']

            # Check stock
            cursor.execute("SELECT qty FROM producttbl WHERE productID = %s", (product_id,))
            result = cursor.fetchone()
            if not result:
                return jsonify({'success': False, 'message': f'Product ID {product_id} not found'})
            
            current_stock = result[0]
            if quantity > current_stock:
                return jsonify({'success': False, 'message': f'Not enough stock for product ID {product_id}'})

            # Insert into cotbl
            cursor.execute("""
                INSERT INTO cotbl (user_id, product_id, quantity, price, sellerID, orderID)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_email, product_id, quantity, price, sellerID, orderID))

            # Update product quantity
            new_stock = current_stock - quantity
            cursor.execute("""
                UPDATE producttbl SET qty = %s WHERE productID = %s
            """, (new_stock, product_id))

        conn.commit()

        #update order history
        update_order_status(orderID, 'order placed')

        cursor.close()
        conn.close()
        print(f"Order successfully placed: {orderID}")

        return jsonify({'success': True, 'message': 'Order placed successfully', 'order_id': orderID})

    except Exception as e:
        print('Error in place_order:', str(e))
        return jsonify({'success': False, 'message': 'Server error occurred'})



#REMOVING ITEMS FROM CART WHEN ORDERED
@app.route('/api/remove-cart-items', methods=['POST'])
def remove_cart_items():
    try:
        data = request.get_json()
        user_email = data.get('email')
        product_ids = data.get('product_ids', [])

        if not product_ids:
            return jsonify({'success': False, 'message': 'No product IDs provided'})

        conn = get_db_connection()
        cursor = conn.cursor()
        for pid in product_ids:
            cursor.execute("DELETE FROM carttbl WHERE user_id = %s AND product_id = %s", (user_email, pid))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Items removed from cart'})

    except Exception as e:
        print('Error in remove_cart_items:', str(e))
        return jsonify({'success': False, 'message': 'Server error'})



#SHOW PRODUCTS TO PAY
@app.route('/api/show_to_pay', methods=['GET'])
def get_orders_to_pay():
    email = request.args.get('email')
    print("Received email:", email)

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT cotbl.orderID, producttbl.prName, producttbl.image_paths, producttbl.prPrice, cotbl.quantity, cotbl.price, cotbl.date
        FROM cotbl 
        JOIN producttbl ON cotbl.product_id = producttbl.productID 
        WHERE cotbl.user_id = %s AND cotbl.status IN ('order placed', 'order approved', 'order packed')
    """, (email,))

    products = cursor.fetchall()
    print("Fetched orders:", products)

    # Add status history per order
    for order in products:
        orderID = order['orderID']
        cursor.execute("""
            SELECT status, updated_at
            FROM status_history
            WHERE orderID = %s
            ORDER BY updated_at DESC
        """, (orderID,))
        history = cursor.fetchall()
        order['status_history'] = history

    cursor.close()
    conn.close()
    return jsonify(products)



#SHOW PRODUCTS TO SHIP
@app.route('/api/show_to_ship', methods=['GET'])
def get_orders_to_ship():
    email = request.args.get('email')
    print("Received email:", email)

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT cotbl.orderID, producttbl.prName, producttbl.image_paths, producttbl.prPrice, cotbl.quantity, cotbl.price, cotbl.date
        FROM cotbl 
        JOIN producttbl ON cotbl.product_id = producttbl.productID 
        WHERE cotbl.user_id = %s AND cotbl.status IN ('order for pick-up', 'order picked-up')
    """, (email,))

    products = cursor.fetchall()
    print("Fetched orders:", products)

    # Add status history per order
    for order in products:
        orderID = order['orderID']
        cursor.execute("""
            SELECT status, updated_at
            FROM status_history
            WHERE orderID = %s
            ORDER BY updated_at DESC
        """, (orderID,))
        history = cursor.fetchall()
        order['status_history'] = history

    cursor.close()
    conn.close()
    return jsonify(products)



#SHOW PRODUCTS TO RECEIVE
@app.route('/api/show_to_receive', methods=['GET'])
def get_orders_to_receive():
    email = request.args.get('email')
    print("Received email:", email)

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT cotbl.orderID, producttbl.prName, producttbl.image_paths, producttbl.prPrice, cotbl.quantity, cotbl.price, cotbl.date
        FROM cotbl 
        JOIN producttbl ON cotbl.product_id = producttbl.productID 
        WHERE cotbl.user_id = %s AND cotbl.status IN ('order on the way', 'order delivered')
    """, (email,))

    products = cursor.fetchall()
    print("Fetched orders:", products)

     # Add status history per order
    for order in products:
        orderID = order['orderID']
        cursor.execute("""
            SELECT status, updated_at
            FROM status_history
            WHERE orderID = %s
            ORDER BY updated_at DESC
        """, (orderID,))
        history = cursor.fetchall()
        order['status_history'] = history

    cursor.close()
    conn.close()
    return jsonify(products)

#CONFIRM ORDER
@app.route('/api/confirm_order', methods=['POST'])
def api_confirm_order():
        data = request.get_json()
        order_id = data.get('orderID')

        if not order_id:
            return jsonify({'message': 'Missing orderID'}), 400

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            datenow = datetime.now()
            new_status = "Order Received"

            # Update order status and received date
            cursor.execute('''
                UPDATE cotbl 
                SET status = %s, received = %s 
                WHERE orderID = %s
            ''', (new_status, datenow, order_id))

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({'message': 'Order confirmed'}), 200

        except Exception as e:
            print("Error in /confirm_order:", e)
            return jsonify({'message': 'Failed to update order'}), 500


#SHOW PRODUCTS TO RATE
@app.route('/api/show_to_rate', methods=['GET'])
def get_orders_to_rate():
    email = request.args.get('email')
    print("Received email:", email)

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT cotbl.orderID, producttbl.productID, producttbl.prName, producttbl.image_paths, producttbl.prPrice, 
                   cotbl.quantity, cotbl.price, cotbl.date, cotbl.sellerID
        FROM cotbl 
        JOIN producttbl ON cotbl.product_id = producttbl.productID
        WHERE cotbl.user_id = %s AND cotbl.status = 'order received'
    """, (email,))

    products = cursor.fetchall()
    print("Fetched orders:", products)

      # Add status history per order
    for order in products:
        orderID = order['orderID']
        cursor.execute("""
            SELECT status, updated_at
            FROM status_history
            WHERE orderID = %s
            ORDER BY updated_at DESC
        """, (orderID,))
        history = cursor.fetchall()
        order['status_history'] = history
        
        
    cursor.close()
    conn.close()
    return jsonify(products)



#FOR THE BUTTON CONFIRM ORDER FEEDBACK FOR BUYER
@app.route('/api/order_feedback', methods=['POST'])
def order_feedback():
    data = request.get_json()

    user_email = data.get('user_email')
    order_id = data.get('order_id')
    product_id = data.get('productID')
    feedback_text = data.get('feedback')
    seller_id = data.get('sellerID')
    reason = data.get('report_reason')

    if not feedback_text:
        return jsonify({'error': 'Feedback is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO feedback (user_id, order_id, product_id, feedback, sellerID) 
        VALUES (%s, %s, %s, %s, %s)
    ''', (user_email, order_id, product_id, feedback_text, seller_id))

    cursor.execute('''
        UPDATE cotbl 
        SET status = 'feedback done'
        WHERE orderID = %s AND product_id = %s
    ''', (order_id, product_id,))

    if reason:
        cursor.execute('SELECT email FROM seller_account WHERE sellerID = %s', (seller_id,))
        seller_email = cursor.fetchone()

        if seller_email:
            seller_email = seller_email[0]
            cursor.execute('''
                INSERT INTO reports (productID, sellerID, buyer, description) 
                VALUES (%s, %s, %s, %s)
            ''', (product_id, seller_email, user_email, reason))

    conn.commit()

    #update order history
    update_order_status(order_id, 'feedback done')

    cursor.close()
    conn.close()

    return jsonify({'message': 'Feedback submitted successfully'}), 200


#SHOW FEEDBACK IN PRODUCT ITEMS
@app.route('/api/get_feedback/<product_id>', methods=['GET'])
def api_get_feedback(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT user_id, feedback 
        FROM feedback 
        WHERE product_id = %s
    ''', (product_id,))
    feedback_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(feedback_list)



#SHOW PRODUCTS COMPLETED
@app.route('/api/show_completed', methods=['GET'])
def get_orders_completed():
    email = request.args.get('email')
    print("Received email:", email)

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("""
        SELECT cotbl.orderID, producttbl.prName, producttbl.image_paths, producttbl.prPrice, cotbl.quantity, cotbl.price, cotbl.date
        FROM cotbl 
        JOIN producttbl ON cotbl.product_id = producttbl.productID 
        WHERE cotbl.user_id = %s AND cotbl.status = 'feedback done'
    """, (email,))

    products = cursor.fetchall()
    print("Fetched orders:", products)

    # Add status history per order
    for order in products:
        orderID = order['orderID']
        cursor.execute("""
            SELECT status, updated_at
            FROM status_history
            WHERE orderID = %s
            ORDER BY updated_at DESC
        """, (orderID,))
        history = cursor.fetchall()
        order['status_history'] = history

    cursor.close()
    conn.close()
    return jsonify(products)



#MESSAGES
@app.route('/api/get_messages', methods=['POST'])
def api_get_messages():
    data = request.get_json()
    buyer_id = data.get('buyer_id')
    seller_id = data.get('seller_id')

    if not buyer_id or not seller_id:
        return jsonify({'success': False, 'message': 'Missing IDs'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        '''
        SELECT * FROM messages
        WHERE (buyer_id = %s AND seller_id = %s)
        ORDER BY id ASC
        ''',
        (buyer_id, seller_id)
    )
    messages = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({'success': True, 'messages': messages})


# Send message
@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    data = request.form
    seller_id = data.get('seller_id')
    buyer_id = data.get('buyer_id')
    message = data.get('message')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO messages (seller_id, buyer_id, message, created_at, role)
        VALUES (%s, %s, %s, %s, 'buyer')
    """, (seller_id, buyer_id, message, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    return "Message sent successfully!"






#-------COURIER ORDERS

@app.route('/api/approved-orders', methods=['GET'])
def get_approved_orders():
    try:
        # Establish database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Execute the query to get approved orders
        cursor.execute("""
            SELECT id, orderID, user_id, region, province, city, brgy,
                   prName, quantity, price, status, date
            FROM cotbl
            WHERE status = 'order approved'
        """)

        # Fetch all rows from the query
        orders = cursor.fetchall()
        cursor.close()
        conn.close()

        # Return the fetched orders as JSON
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        print("Error fetching approved orders:", e)
        return jsonify({'success': False, 'message': 'Server error occurred'})
    

    
#-------COURIER LOGIN


@app.route('/api/courier-login', methods=['POST'])
def courier_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM rider_account WHERE email = %s COLLATE utf8mb4_bin AND password = %s COLLATE utf8mb4_bin",
            (email, password)
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            session['user_email'] = user['email']

            return jsonify({'success': True, 'user': user})

        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print('Error:', str(e))
        return jsonify({'success': False, 'message': 'Server error occurred'}), 500



#------COURIER REGISTER
@app.route('/api/rider_register', methods=['POST'])
def rider_register():
    try:
        data = request.get_json()

        name = data.get('name')
        gender = data.get('gender')
        birthday = data.get('birthday')
        phone = data.get('phone')
        region = data.get('region')
        province = data.get('province')
        city = data.get('city')
        barangay = data.get('barangay')
        street = data.get('street')
        email = data.get('email')
        password = data.get('password')
        confirmpassword = data.get('confirmpassword', password)  # Default to password if not sent

        print("Starting registration...")
        print("User data received:", data)
        print("Passed validation")

        # image = request.files.get('image')
        # image_path = None

        # if image and allowed_file(image.filename):
        #     filename = secure_filename(image.filename)
        #     image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #     image.save(image_path)

        
        if not all([name, gender, birthday, phone, region, province, city, barangay, email, password]):
            return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400

        if password != confirmpassword:
            return jsonify({'status': 'error', 'message': 'Password does not match'}), 400

        password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$'
        if not re.match(password_regex, password):
            return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, and a number.'}), 400

        image_path = ''  # No image
        street = street if street.strip() else None

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM rider_account WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({'status': 'error', 'message': 'Email already registered'}), 400

        try:
            cursor.execute("""
                INSERT INTO rider_account 
                (name, gender, dateofbirth, mobile_no, email, password, image_path, status, address_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending', 0)
            """, (name, gender, birthday, phone, email, password, image_path))
            print("Rider account inserted.")
        except Exception as e:
            print("Error inserting rider_account:", e)
            return jsonify({'status': 'error', 'message': str(e)}), 400


        db.commit()
        rider_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO rider_address (region, province, city, brgy, street, rider_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (region, province, city, barangay, street, rider_id))
        db.commit()
        address_id = cursor.lastrowid

        cursor.execute("UPDATE rider_account SET address_id = %s WHERE id_no = %s", (address_id, rider_id))
        db.commit()
        print("Inserted rider_account with ID:", rider_id)
        cursor.close()
        db.close()

        return jsonify({'status': 'success', 'message': 'Registration successful'}), 200

    except Exception as e:
        print("Registration error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500







#-------COURIER SHOW ORDERS FOR PICK-UP
@app.route('/api/for_pickup', methods=['GET'])
def api_for_pickup():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute('''
            SELECT cotbl.id, cotbl.user_id, cotbl.status, cotbl.orderID, producttbl.prName, 
                   buyer_account.name AS customer_name, 
                   buyer_address.region, buyer_address.province, 
                   buyer_address.city, buyer_address.brgy
            FROM cotbl
            JOIN producttbl ON cotbl.product_id = producttbl.productID
            JOIN buyer_account ON cotbl.user_id = buyer_account.email
            LEFT JOIN buyer_address ON buyer_account.address_id = buyer_address.address_id
            WHERE cotbl.status = 'order for pick-up'
        ''')
        orders = cursor.fetchall()
        return jsonify(orders), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()



#-------COURIER SHOW ORDERS FOR DELIVERY
@app.route('/api/for_delivery', methods=['GET'])
def api_for_delivery():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute('''
            SELECT cotbl.id, cotbl.user_id, cotbl.status, cotbl.orderID, producttbl.prName, 
                   buyer_account.name AS customer_name, 
                   buyer_address.region, buyer_address.province, 
                   buyer_address.city, buyer_address.brgy
            FROM cotbl
            JOIN producttbl ON cotbl.product_id = producttbl.productID
            JOIN buyer_account ON cotbl.user_id = buyer_account.email
            LEFT JOIN buyer_address ON buyer_account.address_id = buyer_address.address_id
            WHERE cotbl.status IN ('shipping order', 'order picked-up', 'order on the way')
        ''')
        orders = cursor.fetchall()
        return jsonify(orders), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()


#COURIER ORDER PICKED UP
@app.route('/api/order_pickedup', methods=['POST'])
def order_sent():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'message': 'Order ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    UPDATE cotbl
    SET status = 'shipping order', shipped = %s
    WHERE orderID = %s AND status = 'order for pick-up'
    """
    cursor.execute(query, (datetime.now(), order_id))
    conn.commit()

    #update order history
    update_order_status(order_id, 'shipping order')

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({'message': 'No matching order found or already marked as shipped'}), 404

    cursor.close()
    conn.close()

    return jsonify({'message': 'Order marked as shipped'})


#COURIER ORDER DISAPPROVE
@app.route('/api/order_disapprove', methods=['POST'])
def order_disapprove():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'message': 'Order ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    UPDATE cotbl
    SET status = 'order packed', shipped = %s
    WHERE orderID = %s AND status = 'order for pick-up'
    """
    cursor.execute(query, (datetime.now(), order_id))
    conn.commit()

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({'message': 'No matching order found'}), 404

    cursor.close()
    conn.close()

    return jsonify({'message': 'Order changed'})


#COURIER SHIP ORDER
@app.route('/api/ship_order', methods=['POST'])
def ship_order():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'message': 'Order ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE cotbl SET status = 'order on the way' 
        WHERE orderID = %s AND status = 'order picked-up'
    """, (order_id,))
    conn.commit()

    cursor.execute("""
        UPDATE cotbl SET status = 'order on the way' 
        WHERE orderID = %s AND status = 'shipping order'
    """, (order_id,))
    conn.commit()

    #update order history
    update_order_status(order_id, 'order on the way')

    if cursor.rowcount == 0:
        return jsonify({'message': 'Order not updated'}), 404

    cursor.close()
    conn.close()

    return jsonify({'message': 'Order is now on the way'}), 200



#COURIER COMPLETE ORDER
@app.route('/api/complete_order', methods=['POST'])
def complete_order():
    data = request.get_json()
    order_id = data.get('order_id')

    if not order_id:
        return jsonify({'message': 'Order ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    UPDATE cotbl
    SET status = 'order delivered', received = %s
    WHERE orderID = %s AND status = 'order on the way'
    """
    cursor.execute(query, (datetime.now(), order_id))
    conn.commit()

    #update order history
    update_order_status(order_id, 'order received')

    if cursor.rowcount == 0:
        cursor.close()
        conn.close()
        return jsonify({'message': 'No matching order found or already marked as received'}), 404

    cursor.close()
    conn.close()

    return jsonify({'message': 'Order marked as received'})


#COURIER
@app.route('/shipping-history', methods=['GET'])
def shipping_history():
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Rider email is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute('''
            SELECT cotbl.id, cotbl.status, cotbl.received, cotbl.orderID, producttbl.prName, 
                   buyer_account.name AS customer_name, 
                   buyer_address.region, buyer_address.province, 
                   buyer_address.city, buyer_address.brgy
            FROM cotbl
            JOIN producttbl ON cotbl.product_id = producttbl.productID
            JOIN buyer_account ON cotbl.user_id = buyer_account.email
            LEFT JOIN buyer_address ON buyer_account.address_id = buyer_address.address_id
            WHERE cotbl.status IN ('order received', 'feedback done')
              AND cotbl.rider_email = %s
            ORDER BY cotbl.received DESC
        ''', (email,))
        
        history = cursor.fetchall()
        return jsonify(history), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



