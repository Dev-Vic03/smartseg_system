import csv
import io
import pandas as pd
from flask import Blueprint, request, jsonify, session, Response
from ml.predictor import predict_segment
from database.models import db, Customer, Segment
from utils.decorators import login_required

prediction_bp = Blueprint('prediction', __name__, url_prefix='/api')


@prediction_bp.route('/predict_single', methods=['POST'])
@login_required
def predict_single():
    user_id = session.get('user_id')
    data = request.get_json() or {}

    recency = data.get('recency')
    frequency = data.get('frequency')
    monetary = data.get('monetary')

    if None in (recency, frequency, monetary):
        return jsonify({'error': 'Missing required RFM parameters.'}), 400

    try:
        result = predict_segment(recency=float(recency), frequency=float(frequency), monetary=float(monetary))
        
        customer_id = data.get('customer_id')
        new_customer = Customer(
            user_id=user_id,
            name=f"Customer #{customer_id}" if customer_id else "Single Inference"
        )
        db.session.add(new_customer)
        db.session.flush()

        segment = Segment(
            customer_id=new_customer.id,
            recency=int(recency),
            frequency=int(frequency),
            monetary=float(monetary),
            cluster_label=result.get('cluster_id', 0),
            segment_name=result.get('segment_name', 'Regular')
        )
        db.session.add(segment)
        db.session.commit()

        return jsonify({'segment_name': result['segment_name']}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@prediction_bp.route('/upload_csv', methods=['POST'], strict_slashes=False)
@login_required
def upload_csv():
    user_id = session.get('user_id')
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File format must be a CSV (.csv)'}), 400

    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip().str.lower()
        
        required_columns = {'recency', 'frequency', 'monetary'}
        if not required_columns.issubset(set(df.columns)):
            return jsonify({'error': f'CSV missing required columns: {list(required_columns)}'}), 400

        processed = 0
        for idx, row in df.iterrows():
            try:
                recency = float(row['recency'])
                frequency = float(row['frequency'])
                monetary = float(row['monetary'])
                cust_id_raw = row.get('customer_id')
                customer_id = int(cust_id_raw) if pd.notna(cust_id_raw) and str(cust_id_raw).isdigit() else None

                result = predict_segment(recency=recency, frequency=frequency, monetary=monetary)

                new_customer = Customer(
                    user_id=user_id,
                    name=f"Customer #{customer_id}" if customer_id else f"Batch Customer #{idx + 1}"
                )
                db.session.add(new_customer)
                db.session.flush()

                segment = Segment(
                    customer_id=new_customer.id,
                    recency=int(recency),
                    frequency=int(frequency),
                    monetary=monetary,
                    cluster_label=result['cluster_id'],
                    segment_name=result['segment_name']
                )
                db.session.add(segment)
                processed += 1
            except Exception:
                db.session.rollback()
                continue

        db.session.commit()
        return jsonify({'processed': processed}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Fatal processing error: {str(e)}"}), 500


@prediction_bp.route('/dashboard_data', methods=['GET'])
@login_required
def get_dashboard_data():
    user_id = session.get('user_id')
    
    # Using flexible pattern matching to support both 'VIP' and 'VIP Customer'
    vip = db.session.query(Segment).join(Customer).filter(Customer.user_id == user_id, Segment.segment_name.ilike('%VIP%')).count()
    loyal = db.session.query(Segment).join(Customer).filter(Customer.user_id == user_id, Segment.segment_name.ilike('%Loyal%')).count()
    regular = db.session.query(Segment).join(Customer).filter(Customer.user_id == user_id, Segment.segment_name.ilike('%Regular%')).count()
    at_risk = db.session.query(Segment).join(Customer).filter(Customer.user_id == user_id, Segment.segment_name.ilike('%At-Risk%')).count()

    recent_records = db.session.query(Customer, Segment)\
        .join(Segment, Customer.id == Segment.customer_id)\
        .filter(Customer.user_id == user_id)\
        .order_by(Customer.id.desc()).limit(5).all()

    recent_data = [{
        'id': cust.id,
        'name': cust.name,
        'recency': seg.recency,
        'frequency': seg.frequency,
        'monetary': seg.monetary,
        'segment': seg.segment_name
    } for cust, seg in recent_records]

    return jsonify({
        'stats': {'vip': vip, 'loyal': loyal, 'regular': regular, 'at_risk': at_risk},
        'recent': recent_data
    }), 200


@prediction_bp.route('/export_all_csv', methods=['GET'])
@login_required
def export_all_csv():
    user_id = session.get('user_id')
    records = db.session.query(Customer, Segment).join(Segment, Customer.id == Segment.customer_id)\
        .filter(Customer.user_id == user_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer ID', 'Name', 'Email', 'Recency', 'Frequency', 'Monetary', 'Segment Name', 'Cluster ID'])

    for cust, seg in records:
        writer.writerow([cust.id, cust.name, getattr(cust, 'email', 'N/A'), seg.recency, seg.frequency, seg.monetary, seg.segment_name, seg.cluster_label])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=all_segmented_customers.csv"}
    )