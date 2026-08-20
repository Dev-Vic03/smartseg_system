import joblib
import numpy as np

scaler = joblib.load('ml/rfm_scaler.pkl')
kmeans = joblib.load('ml/kmeans_model.pkl')

# Map cluster centers to segment names
SEGMENT_MAP = {
    0: 'Regular Customer',
    1: 'VIP Customer',
    2: 'At-Risk Customer',
    3: 'Loyal Customer'
}

def predict_segment(recency, frequency, monetary, user_rfm_pct=None):
    if user_rfm_pct is None:
        # Default relative percentile mapping if raw values passed
        r_pct = min(max(recency / 365.0, 0.0), 1.0)
        f_pct = min(max(frequency / 50.0, 0.0), 1.0)
        m_pct = min(max(monetary / 1000000.0, 0.0), 1.0)
    else:
        r_pct, f_pct, m_pct = user_rfm_pct

    scaled_features = scaler.transform([[r_pct, f_pct, m_pct]])
    cluster_id = int(kmeans.predict(scaled_features)[0])
    segment_name = SEGMENT_MAP.get(cluster_id, 'Regular Customer')

    return {
        'cluster_id': cluster_id,
        'segment_name': segment_name
    }