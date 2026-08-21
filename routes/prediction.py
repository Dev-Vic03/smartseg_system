import csv
import io
import pandas as pd
from flask import Blueprint, request, jsonify, session, Response
from ml.predictor import predict_segment
from database.models import db, Customer, Segment
from utils.decorators import login_required

prediction_bp = Blueprint('prediction', __name__, url_prefix='/api')


# prediction_bp routes (predict_single, upload_csv, dashboard_data) 
# have been heavily optimized and moved to app.py directly to eliminate conflicts.


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