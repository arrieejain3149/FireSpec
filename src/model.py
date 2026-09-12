import xgboost as xgb
import joblib

class FireImpactModel:
    def __init__(self):
        # Hyperparameters chosen for robustness on small tabular dataset
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            random_state=42,
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.8,
            colsample_bytree=0.8
        )

    def fit(self, X_train, y_train):
        self.model.fit(X_train, y_train)

    def predict(self, X):
        return self.model.predict(X)

    def save(self, filepath):
        joblib.dump(self.model, filepath)

    def load(self, filepath):
        self.model = joblib.load(filepath)
