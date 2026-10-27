import os
import re
import glob
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense


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


# 1. Load Data
df = load_dataset()
print(f"Loaded {len(df)} total samples.")

X = df[['dc', 'alpha', 't', 'periodCounter', 'collisions', 'discoveries']].values
y = df['nodes'].values

# Assuming X and y are already loaded as NumPy arrays
assert len(X) == len(y), "X and y must have the same length"

# Generate a shuffled array of indices
indices = np.arange(len(X))
np.random.seed(42)  # Set seed for reproducibility
np.random.shuffle(indices)

# Apply the shuffled indices to both X and y
X_shuffled = X[indices]
y_shuffled = y[indices]

# Now perform your 80/20 split safely
split_idx = int(len(X_shuffled) * 0.8)
X_train, X_test = X_shuffled[:split_idx], X_shuffled[split_idx:]
y_train, y_test = y_shuffled[:split_idx], y_shuffled[split_idx:]

# 2. Scale features manually using training stats (saves mean/std for deployment)
X_mean = X_train.mean(axis=0)
X_std = X_train.std(axis=0)
X_train_scaled = (X_train - X_mean) / X_std
X_test_scaled = (X_test - X_mean) / X_std

# Save scaler parameters so you can use them on your embedded device
np.savez('scaler_params.npz', mean=X_mean, std=X_std)

# 3. Build Tiny MLP Model
model = Sequential([
    Dense(16, activation='relu', input_shape=(6,)),
    Dense(8, activation='relu'),
    Dense(1) # Linear output for node prediction
])

model.compile(optimizer='adam', loss='mse', metrics=['mae'])

# 4. Train
model.fit(X_train_scaled, y_train, epochs=20, batch_size=32, validation_split=0.2)

# 5. Save for local machine testing (.keras or .h5 format)
model.save('node_predictor_model.keras')
print("Model saved locally as 'node_predictor_model.keras'")

# 6. Convert and Save to TensorFlow Lite for Embedded Deployment
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT_WEIGHTS] # Quantize to save space
tflite_model = converter.convert()

with open('node_predictor.tflite', 'wb') as f:
    f.write(tflite_model)
print("Model converted and saved as 'node_predictor.tflite'")
