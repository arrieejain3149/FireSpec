import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

class DataPipeline:
    def __init__(self):
        self.scaler = StandardScaler()
        self.num_features = ['FFMC', 'DMC', 'DC', 'ISI', 'temp', 'RH', 'wind', 'rain']
        
        self.month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                          'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        self.day_map = {'mon': 1, 'tue': 2, 'wed': 3, 'thu': 4, 'fri': 5, 'sat': 6, 'sun': 7}

    def _encode_cyclical(self, df):
        df = df.copy()
        if 'month' in df.columns:
            month_num = df['month'].map(self.month_map)
            df['month_sin'] = np.sin(2 * np.pi * month_num / 12)
            df['month_cos'] = np.cos(2 * np.pi * month_num / 12)
            df = df.drop('month', axis=1)
        if 'day' in df.columns:
            day_num = df['day'].map(self.day_map)
            df['day_sin'] = np.sin(2 * np.pi * day_num / 7)
            df['day_cos'] = np.cos(2 * np.pi * day_num / 7)
            df = df.drop('day', axis=1)
        return df

    def fit_transform(self, X_train):
        """Fits the scaler on training data and transforms it."""
        X_train = self._encode_cyclical(X_train)
        X_train[self.num_features] = self.scaler.fit_transform(X_train[self.num_features])
        return X_train

    def transform(self, X_test):
        """Transforms test data using the fitted scaler (prevents data leakage)."""
        X_test = self._encode_cyclical(X_test)
        X_test[self.num_features] = self.scaler.transform(X_test[self.num_features])
        return X_test

def load_and_split_data(filepath, test_size=0.2, random_state=42):
    """Loads the dataset, splits into train/test, and returns features/target."""
    df = pd.read_csv(filepath)
    
    # Target transformation y = log(1 + area)
    y = np.log1p(df['area'])
    X = df.drop('area', axis=1)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
    return X_train, X_test, y_train, y_test
