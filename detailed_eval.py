import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.metrics import ndcg_score
from pipeline import OperationalRiskEstimator, solve_optimal_dispatch
import warnings
import json

warnings.filterwarnings('ignore')

def detailed_evaluation(df):
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    
    metrics = {
        "overall": {"ndcg": [], "recall": [], "precision": []},
        "monthly": {},
        "capacity_utilization": []
    }
    
    for train_idx, val_idx in kf.split(df):
        tr, val = df.iloc[train_idx].reset_index(drop=True), df.iloc[val_idx].reset_index(drop=True)
        
        model = OperationalRiskEstimator(seed=42) 
        model.fit(tr, tr["area"].values)
        
        scores = model.estimate_hazard(val)
        sel = solve_optimal_dispatch(val, scores, k=25, max_per_cell=4)
        
        # Overall metrics
        k_eval = min(25, len(val_idx))
        ndcg = ndcg_score([val["area"].values], [scores], k=k_eval)
        metrics["overall"]["ndcg"].append(ndcg)
        
        p80 = np.percentile(tr["area"].values, 80, method="linear")
        hi = val["area"].values >= p80
        
        selected_count = np.sum(sel)
        metrics["capacity_utilization"].append(float(selected_count))
        
        true_positives = np.sum((sel == 1) & hi)
        actual_positives = np.sum(hi)
        
        recall = true_positives / actual_positives if actual_positives > 0 else 1.0
        precision = true_positives / selected_count if selected_count > 0 else 0.0
        
        metrics["overall"]["recall"].append(float(recall))
        metrics["overall"]["precision"].append(float(precision))
        
        # Monthly breakdown
        for m in val['month'].unique():
            if m not in metrics["monthly"]:
                metrics["monthly"][m] = {"ndcg": [], "samples": 0}
            
            mask = val['month'] == m
            if np.sum(mask) > 1:
                try:
                    m_ndcg = ndcg_score([val.loc[mask, "area"].values], [scores[mask]])
                    metrics["monthly"][m]["ndcg"].append(m_ndcg)
                except ValueError:
                    pass
            metrics["monthly"][m]["samples"] += np.sum(mask)

    # Aggregate
    report = {
        "Overall Mean NDCG@25": float(np.mean(metrics["overall"]["ndcg"])),
        "Overall Mean Recall@25": float(np.mean(metrics["overall"]["recall"])),
        "Overall Mean Precision@25": float(np.mean(metrics["overall"]["precision"])),
        "Average Crews Dispatched": float(np.mean(metrics["capacity_utilization"])),
        "Monthly NDCG": {m: float(np.mean(v["ndcg"])) if v["ndcg"] else 0.0 for m, v in metrics["monthly"].items()}
    }
    
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    df = pd.read_csv("data/forestfires.csv")
    detailed_evaluation(df)
