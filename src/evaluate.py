import numpy as np
import pandas as pd
from scipy.stats import spearmanr

def dcg_at_k(r, k):
    r = np.asarray(r, dtype=float)[:k]
    if r.size:
        return np.sum(np.subtract(np.power(2, r), 1) / np.log2(np.arange(2, r.size + 2)))
    return 0.

def ndcg_at_k(r, k):
    dcg_max = dcg_at_k(sorted(r, reverse=True), k)
    if not dcg_max:
        return 0.
    return dcg_at_k(r, k) / dcg_max

def evaluate_metrics(y_true, y_pred, y_train, selected_indices, top_k=25):
    """
    Evaluates NDCG@25, Spearman correlation, and High-Impact Recall.
    
    Args:
        y_true: True impact values for the test set.
        y_pred: Predicted impact values for the test set.
        y_train: True impact values for the training set (used for 80th percentile threshold).
        selected_indices: Indices of the rows selected for the response portfolio.
        top_k: K for NDCG (25).
        
    Returns:
        Dictionary of metrics.
    """
    df_eval = pd.DataFrame({'y_true': y_true, 'y_pred': y_pred})
    df_eval_sorted = df_eval.sort_values(by='y_pred', ascending=False)
    
    # NDCG@25 based on sorted predictions
    r = df_eval_sorted['y_true'].values
    ndcg = ndcg_at_k(r, top_k)
    
    # Spearman rank correlation
    spearman, _ = spearmanr(y_true, y_pred)
    
    # High-impact recall within the selected top-25 response set
    threshold = np.percentile(y_train, 80, method='linear')
    high_impact_total = np.sum(y_true >= threshold)
    
    # Get the true values of the selected indices
    # We must ensure selected_indices map to the correct positions in y_true.
    # Assuming selected_indices are positional indices (0 to len(y_true)-1)
    y_selected = np.array(y_true)[selected_indices]
    high_impact_selected = np.sum(y_selected >= threshold)
    
    recall = high_impact_selected / high_impact_total if high_impact_total > 0 else 0
    
    return {
        'ndcg_25': ndcg,
        'spearman': spearman,
        'high_impact_recall': recall
    }
