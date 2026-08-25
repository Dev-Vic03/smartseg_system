import csv
import io
import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from database.models import db, Customer, Sale, Segment
from utils.decorators import login_required, admin_required


customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


def sanitize_search(term):
    """Escapes SQL wildcards from user inputs."""
    return term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
@login_required
def index():
    user_id = session['user_id']
    search_query = request.args.get('search', '').strip()
    segment_filter = request.args.get('segment', '').strip()
    
    query = db.session.query(Customer, Segment).outerjoin(
        Segment, Customer.id == Segment.customer_id
    ).filter(Customer.user_id == user_id)

    if search_query:
        clean_id = search_query.replace('#', '').strip()
        if clean_id.isdigit():
            exact_customer = Customer.query.filter_by(id=int(clean_id), user_id=user_id).first()
            if exact_customer:
                return redirect(url_for('customers.profile', customer_id=exact_customer.id))
            query = query.filter(Customer.id == int(clean_id))
        else:
            query = query.filter(
                (Customer.name.ilike(f"%{search_query}%")) |
                (Customer.email.ilike(f"%{search_query}%")) |
                (Customer.location.ilike(f"%{search_query}%"))
            )
            
    if segment_filter:
        query = query.filter(Segment.segment_name.ilike(f"%{segment_filter}%"))

    # Sorted by ID descending to avoid missing created_at column errors
    records = query.order_by(Customer.id.desc()).all()

    formatted_customers = []
    for cust, seg in records:
        formatted_customers.append({
            'id': cust.id,
            'name': cust.name or f"Customer #{cust.id}",
            'email': cust.email or 'N/A',
            'phone': cust.phone or 'N/A',
            'location': cust.location or 'N/A',
            'recency': seg.recency if seg else 0,
            'frequency': seg.frequency if seg else 0,
            'monetary': seg.monetary if seg else 0.0,
            'segment': seg.segment_name if seg else 'Unassigned'
        })

    return render_template('customers.html', customers=formatted_customers, search_query=search_query, segment_filter=segment_filter)


@customers_bp.route('/<int:customer_id>', methods=['GET'])
@login_required
def profile(customer_id):
    user_id = session['user_id']
    customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first_or_404()
    
    sales = Sale.query.filter_by(customer_id=customer.id).order_by(Sale.sale_date.desc()).all()
    segment = Segment.query.filter_by(customer_id=customer.id).first()
    
    total_spend = sum(sale.price * sale.quantity for sale in sales)

    return render_template(
        'customer_profile.html',
        customer=customer,
        sales=sales,
        segment=segment,
        total_spend=total_spend
    )


@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age_raw = request.form.get('age', '').strip()
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        location = request.form.get('location')
        occupation = request.form.get('occupation')

        if not name:
            flash('Customer name is required.', 'error')
            return render_template('add_customer.html')

        age_parsed = None
        if age_raw:
            try:
                age_parsed = int(age_raw)
            except ValueError:
                flash('Age must be a valid integer number.', 'error')
                return render_template('add_customer.html')

        try:
            new_customer = Customer(
                user_id=session['user_id'],
                name=name,
                age=age_parsed,
                gender=gender,
                phone=phone,
                email=email,
                location=location,
                occupation=occupation
            )
            db.session.add(new_customer)
            db.session.commit()

            flash(f'Customer "{name}" added successfully. Customer ID: {new_customer.id}', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to record customer: {str(e)}', 'error')
            return render_template('add_customer.html')

    return render_template('add_customer.html')


@customers_bp.route('/anonymize/<int:customer_id>', methods=['POST'])
@login_required
@admin_required
def anonymize_customer(customer_id):
    user_id = session['user_id']
    customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first_or_404()

    customer.name = f"Anonymized User #{customer.id}"
    customer.email = f"anonymized_{hashlib.sha256(str(customer.id).encode()).hexdigest()[:8]}@privacy.local"
    customer.phone = "REDACTED"
    customer.is_anonymized = True

    db.session.commit()
    flash(f'Customer ID {customer.id} has been anonymized per privacy guidelines.', 'success')
    return redirect(url_for('customers.profile', customer_id=customer.id))