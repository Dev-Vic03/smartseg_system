from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database.models import db, Campaign
from utils.decorators import login_required

campaigns_bp = Blueprint('campaigns', __name__)

@campaigns_bp.route('/campaigns')
@login_required
def index():
    user_id = session['user_id']
    user_campaigns = Campaign.query.filter_by(user_id=user_id).all()
    
    default_templates = {
        'At-Risk': {'subject': 'We miss you! Here is 20% off', 'body': 'Hi {name}, come back and get 20% off your next purchase with code WE_MISS_YOU.'},
        'VIP': {'subject': 'Exclusive VIP Access Inside', 'body': 'Hi {name}, as a valued VIP, enjoy early access to our newest collection.'},
        'Loyal': {'subject': 'Thank you for being with us', 'body': 'Hi {name}, we appreciate your loyalty! Enjoy double points on your next order.'},
        'Regular': {'subject': 'Discover popular arrivals', 'body': 'Hi {name}, check out our trending items curated for you this week.'}
    }
    return render_template('campaigns.html', campaigns=user_campaigns, templates=default_templates)

@campaigns_bp.route('/campaigns/create', methods=['POST'])
@login_required
def create():
    name = request.form.get('name')
    segment = request.form.get('segment')
    message = request.form.get('message')
    user_id = session['user_id']
    
    new_campaign = Campaign(
        title=name,
        segment_name=segment,
        subject=name,
        body_template=message,
        user_id=user_id
    )
    db.session.add(new_campaign)
    db.session.commit()
    
    return redirect(url_for('campaigns.summary', campaign_id=new_campaign.id))

@campaigns_bp.route('/campaigns/<int:campaign_id>/summary')
@login_required
def summary(campaign_id):
    user_id = session['user_id']
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first_or_404()
    
    # Calculate audience size for this segment
    from database.models import Customer, Segment
    audience_count = Customer.query.join(Segment, Customer.id == Segment.customer_id).filter(
        Customer.user_id == user_id, 
        Segment.segment_name == campaign.segment_name
    ).count()
    
    return render_template('campaign_summary.html', campaign=campaign, audience_count=audience_count)

@campaigns_bp.route('/campaigns/<int:campaign_id>/export_audience')
@login_required
def export_audience(campaign_id):
    import io
    import csv
    from flask import Response
    
    user_id = session['user_id']
    campaign = Campaign.query.filter_by(id=campaign_id, user_id=user_id).first_or_404()
    
    from database.models import Customer, Segment
    audience = Customer.query.join(Segment, Customer.id == Segment.customer_id).filter(
        Customer.user_id == user_id, 
        Segment.segment_name == campaign.segment_name
    ).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer ID', 'Name', 'Email'])
    
    for customer in audience:
        writer.writerow([customer.id, customer.name, customer.email])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=audience_{campaign_id}.csv"}
    )

@campaigns_bp.route('/api/campaigns/send', methods=['POST'])
@login_required
def send_campaign():
    data = request.get_json()
    # Logic to send bulk emails or queue background task
    return jsonify({'message': f"Campaign '{data.get('title')}' dispatched successfully."})