#!/usr/bin/env python3
"""
ALS Matrix Factorization Recommender on MovieLens 100K.
CPU-only. Libraries: NumPy, SciPy, pandas, scikit-learn, requests.
"""
import os, sys, time, json, zipfile, urllib.request, resource
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

SEED = 42
DATA_DIR = "/app/ml-100k"
DATA_FILE = os.path.join(DATA_DIR, "u.data")
DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
ZIP_PATH = "/app/ml-100k.zip"
np.random.seed(SEED)


def download_dataset():
    if os.path.exists(DATA_FILE):
        print("Dataset already exists, skipping download.")
        return
    print("Downloading MovieLens 100K dataset...")
    urllib.request.urlretrieve(DATASET_URL, ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall("/app")
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    print("Download complete.")


def load_and_split():
    df = pd.read_csv(
        DATA_FILE, sep="\t", header=None,
        names=["user_id", "item_id", "rating", "timestamp"],
    )
    df = df[["user_id", "item_id", "rating"]]
    shuffled = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    split = int(len(shuffled) * 0.8)
    train = shuffled.iloc[:split]
    test = shuffled.iloc[split:]
    train.to_csv("/app/train.csv", index=False, header=False)
    test.to_csv("/app/test.csv", index=False, header=False)
    print(f"Train: {len(train)}, Test: {len(test)}")
    return train, test


def build_rating_matrix(train, n_users, n_items, user_map, item_map):
    """Build sparse CSR rating matrix from training data."""
    rows = train["user_id"].map(user_map).values
    cols = train["item_id"].map(item_map).values
    vals = train["rating"].values.astype(np.float32)
    R = sparse.csr_matrix((vals, (rows, cols)), shape=(n_users, n_items))
    return R


def knn_baseline(train, test, n_users, n_items, user_map, item_map, k=20):
    """User-based k-NN collaborative filter with cosine similarity."""
    print("Running k-NN baseline (k=20, cosine)...")
    R_dense = np.zeros((n_users, n_items), dtype=np.float32)
    for _, row in train.iterrows():
        u = user_map[row["user_id"]]
        i = item_map[row["item_id"]]
        R_dense[u, i] = row["rating"]

    # Compute user-user cosine similarity
    sim = cosine_similarity(R_dense)
    np.fill_diagonal(sim, 0)

    # User means (over rated items only)
    rated_mask = (R_dense > 0).astype(np.float32)
    user_sums = R_dense.sum(axis=1)
    user_counts = rated_mask.sum(axis=1)
    user_means = np.divide(user_sums, user_counts, where=user_counts > 0,
                           out=np.zeros_like(user_sums))

    predictions = []
    for _, row in test.iterrows():
        uid, iid, true_r = row["user_id"], row["item_id"], row["rating"]
        if uid not in user_map or iid not in item_map:
            predictions.append((true_r, user_means.mean()))
            continue
        u = user_map[uid]
        i = item_map[iid]
        sims = sim[u]
        # Users who rated item i
        rated_users = np.where(R_dense[:, i] > 0)[0]
        if len(rated_users) == 0:
            predictions.append((true_r, user_means[u]))
            continue
        top_idx = np.argsort(sims[rated_users])[::-1][:k]
        neighbors = rated_users[top_idx]
        neighbor_sims = sims[neighbors]
        if neighbor_sims.sum() == 0:
            predictions.append((true_r, user_means[u]))
            continue
        neighbor_ratings = R_dense[neighbors, i] - user_means[neighbors]
        pred = user_means[u] + np.dot(neighbor_sims, neighbor_ratings) / np.abs(neighbor_sims).sum()
        pred = np.clip(pred, 1, 5)
        predictions.append((true_r, pred))

    true_vals = np.array([p[0] for p in predictions])
    pred_vals = np.array([p[1] for p in predictions])
    rmse = np.sqrt(np.mean((true_vals - pred_vals) ** 2))
    print(f"k-NN Baseline RMSE: {rmse:.4f}")
    return rmse


def als_train(R, rank, reg, iterations):
    """
    ALS matrix factorization on sparse CSR matrix R.
    Returns user_factors (n_users, rank) and item_factors (n_items, rank).
    """
    n_users, n_items = R.shape
    rng = np.random.RandomState(SEED)
    U = rng.normal(0, 0.1, (n_users, rank)).astype(np.float64)
    V = rng.normal(0, 0.1, (n_items, rank)).astype(np.float64)

    Rt = R.T.tocsr()  # item-user matrix for item step
    reg_eye = reg * np.eye(rank, dtype=np.float64)

    for it in range(iterations):
        # Fix V, solve for U
        VtV = V.T @ V + reg_eye
        for u in range(n_users):
            start, end = R.indptr[u], R.indptr[u + 1]
            if start == end:
                continue
            idx = R.indices[start:end]
            ratings = R.data[start:end].astype(np.float64)
            V_u = V[idx]  # (n_rated, rank)
            A = V_u.T @ V_u + reg_eye
            b = V_u.T @ ratings
            U[u] = np.linalg.solve(A, b)

        # Fix U, solve for V
        UtU = U.T @ U + reg_eye
        for i in range(n_items):
            start, end = Rt.indptr[i], Rt.indptr[i + 1]
            if start == end:
                continue
            idx = Rt.indices[start:end]
            ratings = Rt.data[start:end].astype(np.float64)
            U_i = U[idx]  # (n_rated, rank)
            A = U_i.T @ U_i + reg_eye
            b = U_i.T @ ratings
            V[i] = np.linalg.solve(A, b)

        if (it + 1) % 5 == 0 or it == 0:
            # Compute training RMSE for monitoring
            preds = []
            trues = []
            for u in range(n_users):
                start, end = R.indptr[u], R.indptr[u + 1]
                if start == end:
                    continue
                idx = R.indices[start:end]
                ratings = R.data[start:end]
                pred = U[u] @ V[idx].T
                preds.extend(pred.tolist())
                trues.extend(ratings.tolist())
            train_rmse = np.sqrt(np.mean((np.array(trues) - np.array(preds)) ** 2))
            print(f"  ALS iter {it+1}/{iterations}, train RMSE: {train_rmse:.4f}")

    return U.astype(np.float32), V.astype(np.float32)


def evaluate_als(U, V, test, user_map, item_map, global_mean):
    """Evaluate ALS model on test set, return RMSE."""
    true_vals = []
    pred_vals = []
    for _, row in test.iterrows():
        uid, iid, true_r = row["user_id"], row["item_id"], row["rating"]
        if uid in user_map and iid in item_map:
            u = user_map[uid]
            i = item_map[iid]
            pred = float(np.dot(U[u], V[i]))
            pred = np.clip(pred, 1, 5)
        else:
            pred = global_mean
        true_vals.append(true_r)
        pred_vals.append(pred)
    rmse = np.sqrt(np.mean((np.array(true_vals) - np.array(pred_vals)) ** 2))
    return rmse


def measure_latency(U, V, test, user_map, item_map, n_samples=1000):
    """Measure average prediction latency per user-item pair."""
    rng = np.random.RandomState(SEED)
    sample_idx = rng.choice(len(test), size=min(n_samples, len(test)), replace=False)
    sample = test.iloc[sample_idx]

    # Warm up
    for _ in range(10):
        u_idx = user_map.get(sample.iloc[0]["user_id"], 0)
        i_idx = item_map.get(sample.iloc[0]["item_id"], 0)
        _ = float(np.dot(U[u_idx], V[i_idx]))

    start = time.perf_counter()
    for _, row in sample.iterrows():
        uid, iid = row["user_id"], row["item_id"]
        if uid in user_map and iid in item_map:
            u = user_map[uid]
            i = item_map[iid]
            _ = float(np.dot(U[u], V[i]))
    elapsed = time.perf_counter() - start
    latency_ms = (elapsed / len(sample)) * 1000
    return latency_ms


def get_peak_ram_mb():
    """Get peak RAM usage in MB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in KB on Linux
    return usage.ru_maxrss / 1024.0


def generate_recommendations(U, V, train, user_map, item_map, item_map_inv):
    """Generate top-10 recommendations for users 1-5."""
    recs = {}
    for uid in range(1, 6):
        if uid not in user_map:
            recs[str(uid)] = []
            continue
        u = user_map[uid]
        # Items already rated by user in training set
        rated_items = set(
            train[train["user_id"] == uid]["item_id"].values
        )
        scores = U[u] @ V.T  # (n_items,)
        # Mask out already-rated items
        for iid in rated_items:
            if iid in item_map:
                scores[item_map[iid]] = -np.inf
        top_indices = np.argsort(scores)[::-1][:10]
        top_items = [int(item_map_inv[idx]) for idx in top_indices]
        recs[str(uid)] = top_items
    return recs


def main():
    # Step 0: Download dataset
    download_dataset()

    # Step 1: Load and split
    train, test = load_and_split()

    # Build mappings
    all_users = sorted(set(train["user_id"].unique()) | set(test["user_id"].unique()))
    all_items = sorted(set(train["item_id"].unique()) | set(test["item_id"].unique()))
    user_map = {uid: idx for idx, uid in enumerate(all_users)}
    item_map = {iid: idx for idx, iid in enumerate(all_items)}
    item_map_inv = {idx: iid for iid, idx in item_map.items()}
    n_users = len(all_users)
    n_items = len(all_items)
    global_mean = train["rating"].mean()
    print(f"Users: {n_users}, Items: {n_items}, Global mean: {global_mean:.4f}")

    # Step 2: k-NN baseline
    knn_rmse = knn_baseline(train, test, n_users, n_items, user_map, item_map, k=20)

    # Step 3: Build sparse rating matrix
    R = build_rating_matrix(train, n_users, n_items, user_map, item_map)

    # Hyperparameter search - try a few configurations
    configs = [
        (50, 0.1, 20),
        (50, 0.05, 20),
        (50, 0.2, 20),
        (70, 0.1, 20),
        (70, 0.05, 25),
        (30, 0.1, 15),
    ]

    best_rmse = float("inf")
    best_config = None
    best_U = None
    best_V = None
    best_time = 0

    for rank, reg, iters in configs:
        print(f"\nTrying rank={rank}, reg={reg}, iters={iters}")
        t0 = time.time()
        U, V = als_train(R, rank, reg, iters)
        train_time = time.time() - t0
        rmse = evaluate_als(U, V, test, user_map, item_map, global_mean)
        print(f"  Test RMSE: {rmse:.4f}, Time: {train_time:.1f}s")
        if rmse < best_rmse:
            best_rmse = rmse
            best_config = (rank, reg, iters)
            best_U = U.copy()
            best_V = V.copy()
            best_time = train_time

    rank, reg, iters = best_config
    U, V = best_U, best_V
    als_rmse = best_rmse
    training_time = best_time
    print(f"\nBest config: rank={rank}, reg={reg}, iters={iters}")
    print(f"ALS RMSE: {als_rmse:.4f} vs k-NN RMSE: {knn_rmse:.4f}")

    # Step 4: Save model factors
    np.save("/app/user_factors.npy", U)
    np.save("/app/item_factors.npy", V)
    print(f"Saved user_factors.npy {U.shape} and item_factors.npy {V.shape}")

    # Step 5: Measure latency
    latency_ms = measure_latency(U, V, test, user_map, item_map, n_samples=1000)
    peak_ram = get_peak_ram_mb()
    print(f"Prediction latency: {latency_ms:.4f} ms, Peak RAM: {peak_ram:.1f} MB")

    # Write metrics.json
    metrics = {
        "baseline_knn_rmse": round(float(knn_rmse), 4),
        "als_rmse": round(float(als_rmse), 4),
        "training_time_seconds": round(float(training_time), 4),
        "prediction_latency_ms": round(float(latency_ms), 4),
        "peak_ram_mb": round(float(peak_ram), 4),
        "als_rank": int(rank),
        "als_reg": round(float(reg), 4),
        "als_iterations": int(iters),
    }
    with open("/app/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics.json: {json.dumps(metrics, indent=2)}")

    # Step 6: Generate recommendations for users 1-5
    recs = generate_recommendations(U, V, train, user_map, item_map, item_map_inv)
    with open("/app/recommendations.json", "w") as f:
        json.dump(recs, f, indent=2)
    print(f"Saved recommendations.json")

    # Verify ALS beats baseline
    if als_rmse < knn_rmse:
        print(f"\nSUCCESS: ALS ({als_rmse:.4f}) beats k-NN ({knn_rmse:.4f})")
    else:
        print(f"\nWARNING: ALS ({als_rmse:.4f}) did NOT beat k-NN ({knn_rmse:.4f})")

    print("Done!")


if __name__ == "__main__":
    main()
