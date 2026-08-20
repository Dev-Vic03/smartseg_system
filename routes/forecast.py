from flask import Blueprint, render_template, session
from database.models import db, Customer, Segment
from utils.decorators import login_required

forecast_bp = Blueprint('forecast', __name__)

@forecast_bp.route('/forecast', methods=['GET'])
@login_required
def forecast_page():
    user_id = session.get('user_id')

    # Fetch At-Risk customers (where recency exceeds 30-day baseline)
    at_risk_records = db.session.query(Customer, Segment)\
        .join(Segment, Customer.id == Segment.customer_id)\
        .filter(Customer.user_id == user_id, Segment.segment_name == 'At-Risk').all()

    at_risk_customers = [{
        'customer_id': cust.id,
        'segment_name': seg.segment_name,
        'recency': seg.recency,
        'baseline': 30
    } for cust, seg in at_risk_records]

    # Calculate segment projections
    segments = ['VIP', 'Loyal', 'Regular', 'At-Risk']
    multipliers = {'VIP': 1.15, 'Loyal': 1.08, 'Regular': 1.02, 'At-Risk': 0.85}
    projections = []

    for seg_name in segments:
        total = db.session.query(db.func.sum(Segment.monetary))\
            .join(Customer, Customer.id == Segment.customer_id)\
            .filter(Customer.user_id == user_id, Segment.segment_name == seg_name).scalar() or 0.0

        if total > 0:
            projections.append({
                'segment_name': seg_name,
                'current_total': round(total, 2),
                'projected_next_period': round(total * multipliers[seg_name], 2)
            })

    return render_template('forecast.html', at_risk_customers=at_risk_customers, projections=projections)