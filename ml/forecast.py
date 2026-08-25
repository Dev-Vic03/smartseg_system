from database.models import db, Customer, Segment, Sale
from sqlalchemy import func
from datetime import datetime, timedelta


def get_at_risk_customers(user_id):
    """
    Fetches all customers for a given user who belong to the 'At-Risk Customer' segment.
    """
    at_risk_records = db.session.query(Customer, Segment)\
        .join(Segment, Customer.id == Segment.customer_id)\
        .filter(Customer.user_id == user_id, Segment.segment_name == 'At-Risk Customer')\
        .all()

    results = []
    for customer, segment in at_risk_records:
        results.append({
            'customer_id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'recency': segment.recency,
            'frequency': segment.frequency,
            'monetary': segment.monetary
        })

    return results


def project_segment_revenue(user_id):
    """
    Calculates current total revenue per segment and projects growth based on 
    30-day historical sales velocity instead of a fixed multiplier.
    """
    segments = ['VIP Customer', 'Loyal Customer', 'Regular Customer', 'At-Risk Customer']
    projections = []

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    for seg_name in segments:
        # Calculate overall monetary sum
        total_monetary = db.session.query(func.sum(Segment.monetary))\
            .join(Customer, Segment.customer_id == Customer.id)\
            .filter(Customer.user_id == user_id, Segment.segment_name == seg_name)\
            .scalar() or 0.0

        count = db.session.query(Segment)\
            .join(Customer, Segment.customer_id == Customer.id)\
            .filter(Customer.user_id == user_id, Segment.segment_name == seg_name)\
            .count()

        # Calculate recent 30-day velocity from sales records
        recent_sales = db.session.query(func.sum(Sale.price * Sale.quantity))\
            .join(Customer, Sale.customer_id == Customer.id)\
            .join(Segment, Segment.customer_id == Customer.id)\
            .filter(
                Customer.user_id == user_id,
                Segment.segment_name == seg_name,
                Sale.sale_date >= thirty_days_ago
            ).scalar() or 0.0

        # Dynamic growth rate: segment baseline + recent velocity adjustment
        estimated_next_month = total_monetary + recent_sales
        growth_pct = 0
        if total_monetary > 0:
            growth_pct = round(((estimated_next_month - total_monetary) / total_monetary) * 100, 1)

        projections.append({
            'segment_name': seg_name,
            'count': count,
            'current_revenue': round(total_monetary, 2),
            'projected_revenue': round(estimated_next_month, 2),
            'growth_pct': growth_pct
        })

    return projections