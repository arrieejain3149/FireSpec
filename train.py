import os
import joblib
import pandas as pd
from src.data_pipeline import DataPipeline, load_and_split_data
from src.model import FireImpactModel
from src.selector import select_response_portfolio
from src.evaluate import evaluate_metrics

def main():
    print("Loading data...")
    X_train, X_test, y_train, y_test = load_and_split_data('data/forestfires.csv')
    
    # Reset indices for clean positional indexing in selection/evaluation
    X_test = X_test.reset_index(drop=True)
    y_test = y_test.reset_index(drop=True)
    
    # Save the test set for prototype inference
    X_test.to_csv('data/test_features.csv', index=False)
    y_test.to_csv('data/test_target.csv', index=False)
    
    print("Preprocessing data...")
    pipeline = DataPipeline()
    X_train_processed = pipeline.fit_transform(X_train)
    X_test_processed = pipeline.transform(X_test)
    
    print("Training XGBoost Regressor...")
    model = FireImpactModel()
    model.fit(X_train_processed, y_train)
    
    print("Evaluating model on validation split...")
    preds = model.predict(X_test_processed)
    
    selected_indices = select_response_portfolio(X_test, preds, top_n=25, max_per_cell=4)
    metrics = evaluate_metrics(y_test, preds, y_train, selected_indices)
    
    print(f"Metrics:")
    print(f"  NDCG@25:              {metrics['ndcg_25']:.4f}")
    print(f"  Spearman Correlation: {metrics['spearman']:.4f}")
    print(f"  High-Impact Recall:   {metrics['high_impact_recall']:.4f}")
    
    print("Saving artifacts (model, scaler, y_train)...")
    os.makedirs('artifacts', exist_ok=True)
    joblib.dump(pipeline, 'artifacts/pipeline.pkl')
    joblib.dump(y_train, 'artifacts/y_train.pkl') # required for testing threshold
    model.save('artifacts/model.pkl')
    print("Training complete!")

if __name__ == '__main__':
    main()
