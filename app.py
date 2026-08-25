import logging
import io
import csv
import time
from flask import Flask, render_template, session, jsonify, request, flash, redirect, url_for, current_app
from config import Config
from database.models import db, Segment, Customer
from utils.decorators import login_required
from ml.forecast import get_at_risk_customers, project_segment_revenue
from ml.predictor import predict_segment, predict_segment_batch

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

    # Auto-migrate database on boot (Handles adding new columns safely)
    with app.app_context():
        # First ensure all base tables exist (like campaigns, workspace_settings, etc.)
        db.create_all()
        
        from sqlalchemy import text
        
        queries = [
            "ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE NOT NULL",
            "UPDATE users SET is_verified = TRUE",
            "ALTER TABLE users ADD COLUMN verification_code VARCHAR(6)",
            "ALTER TABLE users ADD COLUMN verification_code_expires_at DATETIME"
        ]
        
        with db.engine.begin() as conn:
            for q in queries:
                try:
                    conn.execute(text(q))
                except Exception:
                    pass
        app.logger.info("Database migration check completed.")

    @app.get('/ping')
    def ping():
        return jsonify({"message": "successfully pinged"}), 200

    @app.after_request
    def add_security_headers(response):
        # Prevent the browser from caching protected pages.
        # This ensures that when a user logs out and hits 'Back' or 'Refresh', 
        # the browser MUST ask the server for the page again (which will redirect to login).
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user_id = session['user_id']
        

        # Since data is wiped on logout/refresh, stats start at zero.
        stats = {
            'vip': 0,
            'loyal': 0,
            'regular': 0,
            'at_risk': 0,
        }
        customers = Customer.query.filter_by(user_id=user_id).order_by(Customer.id.desc()).limit(100).all()
        return render_template('dashboard.html', stats=stats, customers=customers)

    @app.route('/api/dashboard_data')
    @login_required
    def dashboard_data():
        user_id = session['user_id']
        
        # 1 Single GROUP BY query for all segment counts (replaces 4 separate queries)
        counts = db.session.query(
            Segment.segment_name, db.func.count(Segment.id)
        ).join(Customer, Segment.customer_id == Customer.id)\
         .filter(Customer.user_id == user_id)\
         .group_by(Segment.segment_name).all()

        stats = {'vip': 0, 'loyal': 0, 'regular': 0, 'at_risk': 0}
        for name, count in counts:
            if name == 'VIP Customer': stats['vip'] = count
            elif name == 'Loyal Customer': stats['loyal'] = count
            elif name == 'Regular Customer': stats['regular'] = count
            elif name == 'At-Risk Customer': stats['at_risk'] = count

        # 1 Query for recent records
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
    @app.route('/api/predict_single', methods=['POST'])
    @login_required
    def predict_single():
        user_id = session['user_id']
        data = request.get_json() or {}
        try:
            recency = float(data.get('recency', 0))
            frequency = float(data.get('frequency', 1))
            monetary = float(data.get('monetary', 0.0))
            customer_id = data.get('customer_id')

            result = predict_segment(recency=recency, frequency=frequency, monetary=monetary)
            
            # Save single prediction synchronously (it's fast enough for 1 record)
            cust = None
            if customer_id:
                cust = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
            if not cust:
                cust = Customer(user_id=user_id, name=f"Customer #{customer_id}" if customer_id else "Single Inference")
                db.session.add(cust)
                db.session.flush()

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

            # Retrieve updated stats to send back instantly
            counts = db.session.query(Segment.segment_name, db.func.count(Segment.id))\
                .join(Customer, Segment.customer_id == Customer.id)\
                .filter(Customer.user_id == user_id)\
                .group_by(Segment.segment_name).all()

            stats = {'vip': 0, 'loyal': 0, 'regular': 0, 'at_risk': 0}
            for name, count in counts:
                if name == 'VIP Customer': stats['vip'] = count
                elif name == 'Loyal Customer': stats['loyal'] = count
                elif name == 'Regular Customer': stats['regular'] = count
                elif name == 'At-Risk Customer': stats['at_risk'] = count

            recent_records = db.session.query(Customer, Segment).outerjoin(Segment, Customer.id == Segment.customer_id)\
                .filter(Customer.user_id == user_id).order_by(Customer.id.desc()).limit(5).all()

            recent_list = []
            for c, s in recent_records:
                recent_list.append({
                    'id': c.id, 'name': c.name, 
                    'recency': s.recency if s else 0, 'frequency': s.frequency if s else 0, 
                    'monetary': s.monetary if s else 0.0, 'segment': s.segment_name if s else 'Unassigned'
                })

            return jsonify({
                'segment_name': result['segment_name'],
                'cluster_id': result.get('cluster_id', 0),
                'stats': stats,
                'recent': recent_list
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    @app.route('/upload_csv', methods=['POST'])
    @app.route('/api/upload_csv', methods=['POST'])
    @login_required
    def upload_csv():
        t_start = time.perf_counter()
        if 'file' not in request.files:
            return jsonify({'error': 'No file submitted'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        user_id = session['user_id']
        processed = 0
        try:
            stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
            csv_input = list(csv.DictReader(stream))
            if not csv_input:
                return jsonify({'processed': 0, 'stats': {'vip': 0, 'loyal': 0, 'regular': 0, 'at_risk': 0}, 'recent': [], 'execution_time_ms': 0})
            
            # Generate unique customer IDs in memory instantly (Zero DB network queries)
            base_id = int(time.time() * 1000) % 100000000
            
            customer_dicts = []
            rfm_batch = []
            
            for i, row in enumerate(csv_input):
                row_lower = {k.lower().strip(): v for k, v in row.items() if k}
                name = row_lower.get('name') or row_lower.get('customer_name') or f"Batch Customer #{i+1}"
                email = row_lower.get('email') or None
                phone = row_lower.get('phone') or None
                location = row_lower.get('location') or None
                
                customer_id = base_id + i + 1
                
                customer_dicts.append({
                    'id': customer_id,
                    'user_id': user_id,
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'location': location,
                    'is_anonymized': False
                })

                recency = float(row_lower.get('recency') or 0)
                frequency = float(row_lower.get('frequency') or 1)
                monetary = float(row_lower.get('monetary') or row_lower.get('spend') or 0.0)
                rfm_batch.append([recency, frequency, monetary])
                
                processed += 1

            stats = {'vip': 0, 'loyal': 0, 'regular': 0, 'at_risk': 0}
            recent = []

            if customer_dicts:
                # 1. INSTANT NumPy ML Predictions in memory
                predictions = predict_segment_batch(rfm_batch)

                segment_dicts = []
                for i, cust_dict in enumerate(customer_dicts):
                    pred = predictions[i]
                    seg_name = pred.get('segment_name', 'Regular Customer')
                    
                    # Count stats in memory
                    if seg_name == 'VIP Customer': stats['vip'] += 1
                    elif seg_name == 'Loyal Customer': stats['loyal'] += 1
                    elif seg_name == 'Regular Customer': stats['regular'] += 1
                    elif seg_name == 'At-Risk Customer': stats['at_risk'] += 1

                    segment_dicts.append({
                        'customer_id': cust_dict['id'],
                        'recency': rfm_batch[i][0],
                        'frequency': rfm_batch[i][1],
                        'monetary': rfm_batch[i][2],
                        'cluster_label': pred.get('cluster_id', 0),
                        'segment_name': seg_name
                    })

                # Prepare top recent 5 records for instant display
                for i in range(min(5, len(customer_dicts))):
                    recent.append({
                        'id': customer_dicts[i]['id'],
                        'name': customer_dicts[i]['name'],
                        'recency': rfm_batch[i][0],
                        'frequency': rfm_batch[i][1],
                        'monetary': rfm_batch[i][2],
                        'segment': predictions[i].get('segment_name', 'Regular Customer')
                    })

                # 2. Async DB Save Thread: Pure background execution with zero thread/session lock contention
                import threading
                def async_db_save(app_obj, c_dicts, s_dicts):
                    with app_obj.app_context():
                        try:
                            with db.engine.begin() as conn:
                                conn.execute(Customer.__table__.insert(), c_dicts)
                                conn.execute(Segment.__table__.insert(), s_dicts)
                        except Exception as ex:
                            app_obj.logger.error(f"Async DB Error: {ex}")

                threading.Thread(target=async_db_save, args=(current_app._get_current_object(), customer_dicts, segment_dicts)).start()

            t_end = time.perf_counter()
            exec_ms = round((t_end - t_start) * 1000, 2)
            current_app.logger.info(f"⚡ FAST IN-MEMORY INFERENCE & RENDER: {exec_ms} ms for {processed} records.")

            # 3. RETURN INSTANT RESPONSE TO USER BEFORE DB FINISHES
            return jsonify({
                'processed': processed,
                'stats': stats,
                'recent': recent,
                'execution_time_ms': exec_ms
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
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

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)