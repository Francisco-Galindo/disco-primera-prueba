import os
import re
import glob
import pandas as pd
import numpy as np
import tensorflow as tf

def parse_folder_params(folder_name):
    dc_match = re.search(r'([\d\.]+)-dc', folder_name)
    alpha_match = re.search(r'([\d\.]+)-alpha', folder_name)
    t_match = re.search(r'([\d\.]+)-t', folder_name)

    return {
        'dc': float(dc_match.group(1)) if dc_match else 0.0,
        'alpha': float(alpha_match.group(1)) if alpha_match else 0.0,
        't': float(t_match.group(1)) if t_match else 0.0
    }

def load_dataset(base_dir="exp-data"):
    data_rows = []
    for folder_path in glob.glob(os.path.join(base_dir, "reward-static-*")):
        folder_name = os.path.basename(folder_path)
        params = parse_folder_params(folder_name)

        for file_path in glob.glob(os.path.join(folder_path, "*-nodes-history.data")):
            file_name = os.path.basename(file_path)
            nodes_match = re.search(r'(\d+)-nodes', file_name)
            if not nodes_match:
                continue
            nodes = int(nodes_match.group(1))

            with open(file_path, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 3:
                        try:
                            period, collisions, discoveries = map(float, parts)
                            data_rows.append({
                                'dc': params['dc'],
                                'alpha': params['alpha'],
                                't': params['t'],
                                'periodCounter': period,
                                'collisions': collisions,
                                'discoveries': discoveries,
                                'nodes': nodes
                            })
                        except ValueError:
                            continue
    return pd.DataFrame(data_rows)

print("Loading dataset for evaluation...")
df = load_dataset()

X = df[['dc', 'alpha', 't', 'periodCounter', 'collisions', 'discoveries']].values
y = df['nodes'].values

# 1. Apply the exact same shuffling and split used during training
np.random.seed(42)
indices = np.arange(len(X))
np.random.shuffle(indices)

X_shuffled = X[indices]
y_shuffled = y[indices]

split_idx = int(len(X_shuffled) * 0.8)
X_test = X_shuffled[split_idx:]
y_test = y_shuffled[split_idx:]

# 2. Load the saved model and scaler parameters
print("Loading model and scaler parameters...")
model = tf.keras.models.load_model('node_predictor_model.keras')
scaler_data = np.load('scaler_params.npz')
mean, std = scaler_data['mean'], scaler_data['std']

# 3. Scale test data
X_test_scaled = (X_test - mean) / std

# 4. Evaluate overall performance
print("\n--- Evaluating Model on Test Set ---")
test_loss, test_mae = model.evaluate(X_test_scaled, y_test, verbose=0)
print(f"Mean Squared Error (Loss): {test_loss:.4f}")
print(f"Mean Absolute Error (MAE): {test_mae:.4f}")

# 5. Print side-by-side comparison of a few test predictions
print("\n--- Sample Predictions vs Actual Nodes ---")
predictions = model.predict(X_test_scaled, verbose=0)

print(f"{'Actual Nodes':<15} | {'Predicted Nodes':<15} | {'Absolute Error':<15}")
print("-" * 51)
for i in range(10):
    actual = y_test[i]
    pred = predictions[i][0]
    error = abs(actual - pred)
    print(f"{actual:<15} | {pred:<15.2f} | {error:<15.2f}")
