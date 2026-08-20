import csv
import io
from flask import Blueprint, render_template, Response, session
from database.models import db, Customer, Segment
from utils.decorators import login_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    user_id = session['user_id']
    total_cust = Customer.query.filter_by(user_id=user_id).count()
    
    segments = db.session.query(
        Segment.segment_name, db.func.count(Segment.id), db.func.sum(Segment.monetary)
    ).join(Customer, Customer.id == Segment.customer_id)\
     .filter(Customer.user_id == user_id)\
     .group_by(Segment.segment_name).all()

    summary_data = []
    for name, count, total_spend in segments:
        spend = total_spend or 0.0
        summary_data.append({
            'name': name,
            'count': count,
            'total_spend': spend,
            'avg_spend': (spend / count) if count else 0.0
        })

    return render_template('reports.html', total_cust=total_cust, summary=summary_data)

@reports_bp.route('/export/csv')
@login_required
def export_csv():
    user_id = session['user_id']
    results = db.session.query(Customer, Segment).outerjoin(
        Segment, Customer.id == Segment.customer_id
    ).filter(Customer.user_id == user_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer ID', 'Name', 'Email', 'Location', 'Recency (Days)', 'Frequency (Orders)', 'Monetary ($ Total Spend)', 'Segment Name'])

    for cust, seg in results:
        writer.writerow([
            cust.id, 
            cust.name or 'N/A',
            cust.email or 'N/A',
            cust.location or 'N/A',
            seg.recency if seg else 0,
            seg.frequency if seg else 0,
            seg.monetary if seg else 0.0,
            seg.segment_name if seg else 'Unassigned'
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=smartseg_customer_analytics.csv"}
    )

@reports_bp.route('/executive_summary')
@login_required
def executive_summary():
    user_id = session['user_id']
    total_cust = Customer.query.filter_by(user_id=user_id).count()
    
    segments = db.session.query(
        Segment.segment_name, db.func.count(Segment.id), db.func.sum(Segment.monetary)
    ).join(Customer, Customer.id == Segment.customer_id)\
     .filter(Customer.user_id == user_id)\
     .group_by(Segment.segment_name).all()

    summary_data = []
    total_revenue = 0.0
    for name, count, spend in segments:
        s_spend = spend or 0.0
        total_revenue += s_spend
        summary_data.append({
            'name': name,
            'count': count,
            'revenue': s_spend,
            'percentage': round((count / total_cust * 100), 1) if total_cust else 0
        })

    return render_template('executive_report.html', total_cust=total_cust, total_revenue=total_revenue, segments=summary_data)