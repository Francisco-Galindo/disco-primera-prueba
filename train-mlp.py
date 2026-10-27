import os
import re
import glob
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam

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
print("Loading dataset...")
df = load_dataset()
print(f"Loaded {len(df)} total samples.")

X = df[['dc', 'alpha', 't', 'periodCounter', 'collisions', 'discoveries']].values
y = df['nodes'].values

# 2. Shuffle securely with a fixed seed
np.random.seed(42)
indices = np.arange(len(X))
np.random.shuffle(indices)
X_shuffled = X[indices]
y_shuffled = y[indices]

# 3. Train/Test Split (80% train, 20% test)
split_idx = int(len(X_shuffled) * 0.8)
X_train, X_test = X_shuffled[:split_idx], X_shuffled[split_idx:]
y_train, y_test = y_shuffled[:split_idx], y_shuffled[split_idx:]

# 4. Scale Features (X) and Target (y) STRICTLY on training data
X_mean = X_train.mean(axis=0)
X_std = X_train.std(axis=0)
y_mean = y_train.mean()
y_std = y_train.std()

X_train_scaled = (X_train - X_mean) / X_std
X_test_scaled = (X_test - X_mean) / X_std

y_train_scaled = (y_train - y_mean) / y_std
y_test_scaled = (y_test - y_mean) / y_std

# Save scalers and test set for future inspection
np.savez('scaler_params.npz',
         X_mean=X_mean, X_std=X_std,
         y_mean=y_mean, y_std=y_std)
np.savez('test_set.npz', X_test=X_test, y_test=y_test)

# 5. Build Tiny MLP Model
model = Sequential([
    Dense(16, activation='relu', input_shape=(6,)),
    Dense(8, activation='relu'),
    Dense(1) # Linear output for node prediction
])

model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])

# 6. Train Model
print("Training model...")
model.fit(
    X_train_scaled, y_train_scaled,
    epochs=40,
    batch_size=32,
    validation_split=0.2,
    verbose=1
)

# 7. Evaluate on Untouched Test Set (Inverse transforming predictions back to real scale)
print("\n--- Evaluating on Untouched Test Set ---")
predictions_scaled = model.predict(X_test_scaled, verbose=0)
predictions = (predictions_scaled.flatten() * y_std) + y_mean

mse = np.mean((y_test - predictions) ** 2)
mae = np.mean(np.abs(y_test - predictions))

print(f"Test Mean Squared Error (MSE): {mse:.4f}")
print(f"Test Mean Absolute Error (MAE): {mae:.4f}")

# Print sample comparisons
print("\n--- Sample Predictions vs Actual Nodes ---")
print(f"{'Actual Nodes':<15} | {'Predicted Nodes':<15} | {'Absolute Error':<15}")
print("-" * 51)
for i in range(10):
    actual = y_test[i]
    pred = predictions[i]
    error = abs(actual - pred)
    print(f"{actual:<15} | {pred:<15.2f} | {error:<15.2f}")

# 8. Save Models (.keras and .tflite)
model.save('node_predictor_model.keras')
print("\nModel saved locally as 'node_predictor_model.keras'")

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT_WEIGHTS]
tflite_model = converter.convert()

with open('node_predictor.tflite', 'wb') as f:
    f.write(tflite_model)
print("Model converted and saved as 'node_predictor.tflite'")
