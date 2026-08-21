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

def predict_segment_batch(rfm_batch):
    """
    Predict segments for a batch of RFM values to optimize processing.
    rfm_batch should be a list of lists or tuples: [(recency, frequency, monetary), ...]
    """
    if not rfm_batch:
        return []

    # Apply percentile mapping vectorized
    batch_array = np.array(rfm_batch, dtype=float)
    
    # Clip and normalize
    r_pct = np.clip(batch_array[:, 0] / 365.0, 0.0, 1.0)
    f_pct = np.clip(batch_array[:, 1] / 50.0, 0.0, 1.0)
    m_pct = np.clip(batch_array[:, 2] / 1000000.0, 0.0, 1.0)
    
    # Stack into feature matrix
    features = np.column_stack((r_pct, f_pct, m_pct))
    
    # Scale and predict
    scaled_features = scaler.transform(features)
    cluster_ids = kmeans.predict(scaled_features)
    
    results = []
    for cluster_id in cluster_ids:
        results.append({
            'cluster_id': int(cluster_id),
            'segment_name': SEGMENT_MAP.get(int(cluster_id), 'Regular Customer')
        })
        
    return results