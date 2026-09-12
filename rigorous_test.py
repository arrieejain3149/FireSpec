import numpy as np
import pandas as pd
from sklearn.model_selection import RepeatedKFold
from sklearn.metrics import ndcg_score
from pipeline import OperationalRiskEstimator, solve_optimal_dispatch
import time
import warnings

# Suppress sklearn/scipy warnings for clean output
warnings.filterwarnings('ignore')

def rigorous_evaluation(df):
    print("Starting Rigorous Evaluation (10 splits x 3 repeats = 30 folds)...")
    rkf = RepeatedKFold(n_splits=10, n_repeats=3, random_state=42)
    
    ndcgs = []
    recalls = []
    
    start_time = time.time()
    
    for fold, (train_idx, val_idx) in enumerate(rkf.split(df)):
        tr, val = df.iloc[train_idx].reset_index(drop=True), df.iloc[val_idx].reset_index(drop=True)
        
        # Train
        model = OperationalRiskEstimator(seed=fold) 
        model.fit(tr, tr["area"].values)
        
        # Predict
        scores = model.estimate_hazard(val)
        sel = solve_optimal_dispatch(val, scores)
        
        # Metrics - Ranking
        k_eval = min(25, len(val_idx))
        ndcg = ndcg_score([val["area"].values], [scores], k=k_eval)
        ndcgs.append(ndcg)
        
        # Metrics - Recall
        p80 = np.percentile(tr["area"].values, 80, method="linear")
        hi = val["area"].values >= p80
        recall = np.sum((sel == 1) & hi) / np.sum(hi) if np.sum(hi) > 0 else 1.0
        recalls.append(recall)
        
    elapsed = time.time() - start_time
    print("-" * 50)
    print("RIGOROUS EVALUATION RESULTS (30 FOLDS)")
    print(f"Total time   : {elapsed:.2f} seconds")
    print(f"Mean NDCG@25 : {np.mean(ndcgs):.4f} (Std: {np.std(ndcgs):.4f})")
    print(f"Min NDCG@25  : {np.min(ndcgs):.4f} (Worst-case fold)")
    print(f"Max NDCG@25  : {np.max(ndcgs):.4f} (Best-case fold)")
    print(f"Mean Recall  : {np.mean(recalls):.4f} (Std: {np.std(recalls):.4f})")
    print("-" * 50)

if __name__ == "__main__":
    df = pd.read_csv("data/forestfires.csv")
    rigorous_evaluation(df)
