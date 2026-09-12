import pandas as pd

def select_response_portfolio(df, predictions, top_n=25, max_per_cell=4):
    """
    Selects top_n rows based on predictions, with at most max_per_cell from the same (X, Y) cell.
    
    Args:
        df: DataFrame containing at least 'X' and 'Y' columns.
        predictions: Array of predicted impact scores.
        top_n: Exact number of observations to select.
        max_per_cell: Maximum number of observations allowed per (X, Y) cell.
        
    Returns:
        A list of selected indices from the original DataFrame.
    """
    # Create a copy and attach predictions to sort by them
    df_eval = df.copy()
    df_eval['pred_impact'] = predictions
    df_eval['original_index'] = df_eval.index
    
    # Sort descending by predicted impact
    df_sorted = df_eval.sort_values(by='pred_impact', ascending=False)
    
    selected_indices = []
    cell_counts = {}
    
    for _, row in df_sorted.iterrows():
        cell = (row['X'], row['Y'])
        
        if cell not in cell_counts:
            cell_counts[cell] = 0
            
        if cell_counts[cell] < max_per_cell:
            selected_indices.append(row['original_index'])
            cell_counts[cell] += 1
            
        if len(selected_indices) == top_n:
            break
            
    return selected_indices
