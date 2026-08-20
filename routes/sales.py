from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.models import db, Customer, Sale, Segment
from ml.predictor import predict_segment
from utils.decorators import login_required

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


@sales_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    user_id = session['user_id']
    customer_id = request.args.get('customer_id', type=int)

    if request.method == 'POST':
        cust_id = request.form.get('customer_id', type=int)
        item_name = request.form.get('item_name', '').strip()
        quantity = request.form.get('quantity', type=int, default=1)
        price = request.form.get('price', type=float, default=0.0)

        customer = Customer.query.filter_by(id=cust_id, user_id=user_id).first()
        if not customer:
            flash('Invalid Customer ID or permission denied.', 'error')
            return redirect(url_for('sales.add_sale'))

        try:
            # 1. Record Sale
            new_sale = Sale(
                customer_id=customer.id,
                item_name=item_name,
                quantity=quantity,
                price=price,
                sale_date=datetime.utcnow()
            )
            db.session.add(new_sale)
            db.session.flush()

            # 2. Recalculate RFM values for Customer
            all_sales = Sale.query.filter_by(customer_id=customer.id).all()
            total_monetary = sum(s.price * s.quantity for s in all_sales)
            total_frequency = len(all_sales)
            recency_days = 0  # Just purchased

            # 3. Update or Create Segment Entry with ML Engine
            prediction = predict_segment(recency=recency_days, frequency=total_frequency, monetary=total_monetary)
            
            segment = Segment.query.filter_by(customer_id=customer.id).first()
            if not segment:
                segment = Segment(customer_id=customer.id)
                db.session.add(segment)

            segment.recency = recency_days
            segment.frequency = total_frequency
            segment.monetary = total_monetary
            segment.cluster_label = prediction['cluster_id']
            segment.segment_name = prediction['segment_name']

            db.session.commit()
            flash(f'Sale recorded successfully! Customer segment updated to {prediction["segment_name"]}.', 'success')
            return redirect(url_for('customers.profile', customer_id=customer.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to log transaction: {str(e)}', 'error')

    customers = Customer.query.filter_by(user_id=user_id).order_by(Customer.name.asc()).all()
    return render_template('add_sale.html', customers=customers, selected_customer_id=customer_id)