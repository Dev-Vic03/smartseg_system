import os
import numpy as np
import pandas as pd
import joblib
import sklearn
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

print("=== Training Environment Versions ===")
print(f"NumPy: {np.__version__}")
print(f"Pandas: {pd.__version__}")
print(f"Scikit-Learn: {sklearn.__version__}")
print(f"Joblib: {joblib.__version__}")
print("====================================")


def load_dataset(data_path):
    """Loads CSV or XLSX datasets and standardizes variable column names."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"File not found at: {data_path}")

    # Read file dynamically based on file extension
    if data_path.endswith('.xlsx') or data_path.endswith('.xls'):
        df = pd.read_excel(data_path)
    else:
        try:
            df = pd.read_csv(data_path, encoding='latin1', engine='python', on_bad_lines='skip')
        except Exception:
            df = pd.read_csv(data_path, encoding='utf-8', engine='python', on_bad_lines='skip')

    # Standardize column names (lowercase, stripped of spaces and underscores)
    column_map = {}
    for col in df.columns:
        clean_col = str(col).strip().lower().replace(' ', '').replace('_', '')
        if 'customer' in clean_col:
            column_map[col] = 'customer_id'
        elif 'date' in clean_col:
            column_map[col] = 'invoice_date'
        elif 'quantity' in clean_col or 'qty' in clean_col:
            column_map[col] = 'quantity'
        elif 'price' in clean_col or 'unit' in clean_col or 'amount' in clean_col:
            column_map[col] = 'unit_price'

    df = df.rename(columns=column_map)

    # Verify required columns exist
    required_cols = {'customer_id', 'invoice_date', 'quantity', 'unit_price'}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Could not map required columns: {missing_cols}. Found columns in dataset: {list(df.columns)}"
        )

    # Clean missing records and convert data types
    df = df.dropna(subset=['customer_id', 'invoice_date'])
    df['customer_id'] = df['customer_id'].astype(int)
    df['invoice_date'] = pd.to_datetime(df['invoice_date'])
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0)

    # Filter out returns, cancellations, or invalid rows
    df = df[(df['quantity'] > 0) & (df['unit_price'] > 0)]

    return df


def train_and_save_pipeline(file_path):
    # 1. Load and clean raw data
    df = load_dataset(file_path)
    print(f"Successfully processed {len(df)} transaction records.")

    # 2. Compute RFM Aggregations
    ref_date = df['invoice_date'].max() + pd.Timedelta(days=1)
    df['total_spend'] = df['quantity'] * df['unit_price']

    rfm = df.groupby('customer_id').agg({
        'invoice_date': lambda x: (ref_date - x.max()).days,
        'customer_id': 'count',
        'total_spend': 'sum'
    }).rename(columns={
        'invoice_date': 'recency',
        'customer_id': 'frequency',
        'total_spend': 'monetary'
    }).reset_index()

    # 3. Dynamic Scale-Agnostic Percentile Normalization (Percentiles 0.0 to 1.0)
    rfm['r_percentile'] = rfm['recency'].rank(pct=True)
    rfm['f_percentile'] = rfm['frequency'].rank(pct=True)
    rfm['m_percentile'] = rfm['monetary'].rank(pct=True)

    X = rfm[['r_percentile', 'f_percentile', 'm_percentile']].values

    # 4. Train / Test / Validation Split (70% Train, 20% Test, 10% Validation)
    X_train, X_temp = train_test_split(X, test_size=0.30, random_state=42)
    X_test, X_val = train_test_split(X_temp, test_size=0.3333, random_state=42)

    # 5. Fit Scaler and K-Means Model
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    kmeans.fit(X_train_scaled)

    # 6. Evaluate on Held-out Test Set
    test_labels = kmeans.predict(X_test_scaled)
    print("\n--- Held-Out Test Set Evaluation Metrics ---")
    print(f"Silhouette Score:        {silhouette_score(X_test_scaled, test_labels):.4f}")
    print(f"Davies-Bouldin Index:    {davies_bouldin_score(X_test_scaled, test_labels):.4f}")
    print(f"Calinski-Harabasz Index: {calinski_harabasz_score(X_test_scaled, test_labels):.4f}")

    # 7. Save Model Artifacts
    os.makedirs('ml', exist_ok=True)
    joblib.dump(scaler, 'ml/rfm_scaler.pkl')
    joblib.dump(kmeans, 'ml/kmeans_model.pkl')
    print("\nModel artifacts successfully saved to 'ml/rfm_scaler.pkl' and 'ml/kmeans_model.pkl'.")


if __name__ == '__main__':
    # Checks for Excel or CSV files in the data directory
    DATASET_PATH = 'data/transactions.xlsx'

    if not os.path.exists(DATASET_PATH) and os.path.exists('data/transactions.csv'):
        DATASET_PATH = 'data/transactions.csv'

    train_and_save_pipeline(DATASET_PATH)