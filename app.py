import logging
import io
import csv
from flask import Flask, render_template, session, jsonify, request
from config import Config
from database.models import db, Segment, Customer
from utils.decorators import login_required
from ml.forecast import get_at_risk_customers, project_segment_revenue
from ml.predictor import predict_segment

# Route Blueprints
from routes.prediction import prediction_bp
from routes.auth import auth_bp, mail
from routes.customers import customers_bp
from routes.campaigns import campaigns_bp
from routes.reports import reports_bp
from routes.settings import settings_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    app.logger.info("Initializing SmartSeg Core Application...")

    db.init_app(app)
    mail.init_app(app)

    # Register Blueprints
    app.register_blueprint(prediction_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    with app.app_context():
        db.create_all()

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user_id = session['user_id']
        base_query = Segment.query.join(Customer, Segment.customer_id == Customer.id).filter(Customer.user_id == user_id)
        stats = {
            'vip': base_query.filter(Segment.segment_name == 'VIP Customer').count(),
            'loyal': base_query.filter(Segment.segment_name == 'Loyal Customer').count(),
            'regular': base_query.filter(Segment.segment_name == 'Regular Customer').count(),
            'at_risk': base_query.filter(Segment.segment_name == 'At-Risk Customer').count(),
        }
        return render_template('dashboard.html', stats=stats)

    @app.route('/api/dashboard_data')
    @login_required
    def dashboard_data():
        user_id = session['user_id']
        base_query = Segment.query.join(Customer, Segment.customer_id == Customer.id).filter(Customer.user_id == user_id)
        stats = {
            'vip': base_query.filter(Segment.segment_name == 'VIP Customer').count(),
            'loyal': base_query.filter(Segment.segment_name == 'Loyal Customer').count(),
            'regular': base_query.filter(Segment.segment_name == 'Regular Customer').count(),
            'at_risk': base_query.filter(Segment.segment_name == 'At-Risk Customer').count(),
        }
        recent_records = db.session.query(Customer, Segment).outerjoin(
            Segment, Customer.id == Segment.customer_id
        ).filter(Customer.user_id == user_id).order_by(Customer.id.desc()).limit(5).all()

        recent_list = []
        for cust, seg in recent_records:
            recent_list.append({
                'id': cust.id,
                'name': cust.name,
                'recency': seg.recency if seg else 0,
                'frequency': seg.frequency if seg else 0,
                'monetary': seg.monetary if seg else 0.0,
                'segment': seg.segment_name if seg else 'Unassigned'
            })

        return jsonify({'stats': stats, 'recent': recent_list})

    @app.route('/predict_single', methods=['POST'])
    @login_required
    def predict_single():
        data = request.get_json() or {}
        try:
            recency = float(data.get('recency', 0))
            frequency = float(data.get('frequency', 1))
            monetary = float(data.get('monetary', 0.0))
            customer_id = data.get('customer_id')

            result = predict_segment(recency=recency, frequency=frequency, monetary=monetary)
            
            if customer_id:
                cust = Customer.query.filter_by(id=customer_id, user_id=session['user_id']).first()
                if cust:
                    seg = Segment.query.filter_by(customer_id=cust.id).first()
                    if not seg:
                        seg = Segment(customer_id=cust.id)
                        db.session.add(seg)
                    seg.recency = recency
                    seg.frequency = frequency
                    seg.monetary = monetary
                    seg.cluster_label = result.get('cluster_id', 0)
                    seg.segment_name = result.get('segment_name', 'Regular Customer')
                    db.session.commit()

            return jsonify({
                'segment_name': result['segment_name'],
                'cluster_id': result.get('cluster_id', 0)
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    @app.route('/upload_csv', methods=['POST'])
    @login_required
    def upload_csv():
        if 'file' not in request.files:
            return jsonify({'error': 'No file submitted'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        user_id = session['user_id']
        processed = 0
        try:
            stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            for row in csv_input:
                row_lower = {k.lower().strip(): v for k, v in row.items() if k}
                name = row_lower.get('name') or row_lower.get('customer_name') or f"Batch Customer #{processed+1}"
                email = row_lower.get('email') or None
                phone = row_lower.get('phone') or None
                location = row_lower.get('location') or None
                
                cust = Customer(
                    user_id=user_id,
                    name=name,
                    email=email,
                    phone=phone,
                    location=location,
                    is_anonymized=False
                )
                db.session.add(cust)
                db.session.flush()

                recency = float(row_lower.get('recency') or 0)
                frequency = float(row_lower.get('frequency') or 1)
                monetary = float(row_lower.get('monetary') or row_lower.get('spend') or 0.0)

                res = predict_segment(recency=recency, frequency=frequency, monetary=monetary)

                seg = Segment(
                    customer_id=cust.id,
                    recency=recency,
                    frequency=frequency,
                    monetary=monetary,
                    cluster_label=res.get('cluster_id', 0),
                    segment_name=res.get('segment_name', 'Regular Customer')
                )
                db.session.add(seg)
                processed += 1

            db.session.commit()
            return jsonify({'processed': processed})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    @app.route('/forecast')
    @login_required
    def forecast():
        user_id = session['user_id']
        total_segments = Segment.query.join(Customer, Segment.customer_id == Customer.id).filter(Customer.user_id == user_id).count()
        
        if total_segments == 0:
            return render_template(
                'forecast.html',
                at_risk_customers=[],
                projections={'vip': 0, 'loyal': 0, 'regular': 0, 'at_risk': 0}
            )

        return render_template(
            'forecast.html',
            at_risk_customers=get_at_risk_customers(user_id),
            projections=project_segment_revenue(user_id)
        )

    @app.route('/terms')
    def terms():
        return render_template('terms.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)