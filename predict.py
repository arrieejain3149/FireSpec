import joblib
import pandas as pd
from src.model import FireImpactModel
from src.selector import select_response_portfolio

def predict_portfolio(features_path, output_path='data/selected_portfolio.csv'):
    print(f"Loading test features from {features_path}...")
    X_test = pd.read_csv(features_path)
    
    print("Loading artifacts...")
    pipeline = joblib.load('artifacts/pipeline.pkl')
    model = FireImpactModel()
    model.load('artifacts/model.pkl')
    
    print("Preprocessing and Predicting...")
    X_test_processed = pipeline.transform(X_test)
    preds = model.predict(X_test_processed)
    
    print("Selecting constrained portfolio...")
    selected_indices = select_response_portfolio(X_test, preds, top_n=25, max_per_cell=4)
    
    # Generate the output dataframe
    portfolio = X_test.iloc[selected_indices].copy()
    portfolio['predicted_impact'] = preds[selected_indices]
    
    # Note: Target values are NOT used anywhere in this process, ensuring no data leakage.
    
    portfolio.to_csv(output_path, index=False)
    print(f"Portfolio saved to {output_path}")
    return portfolio

if __name__ == '__main__':
    predict_portfolio('data/test_features.csv')
