# Wildfire Response Prioritization - Technical Explanation & Robustness Analysis

## Technical Explanation
The core task is to identify and respond to the most impactful wildfires given limited resources and geographic constraints.

### 1. The Regression Analogy
While the final goal is to rank fires and select a top-25 portfolio, treating this purely as a classification or listwise learning-to-rank problem is suboptimal given the small tabular dataset. Instead, we use a **regression approach**. We predict the target $y = \log(1 + \text{area})$. 
Predicting the continuous impact provides an inherent, fine-grained ranking score. By sorting the continuous regression predictions descendingly, we effectively generate our ranked priority list.

### 2. Preprocessing & Leakage Prevention
Data leakage is strictly prevented. The `StandardScaler` used to normalize meteorological features (temp, RH, wind) is `fit` exclusively on the training partition. Categorical cyclical features (month, day) are mapped to continuous sine/cosine values to capture their cyclic nature (e.g., December is temporally close to January).

### 3. Model
We use an `XGBRegressor`. Tree-based gradient boosting is highly effective on tabular meteorological data because it captures non-linear interactions between features (e.g., high wind *and* low humidity compounding fire spread).

### 4. Selection Mechanism
The maximum 4-per-cell constraint is enforced via a fast Greedy Selection Algorithm. After sorting observations by predicted impact, we iterate downward, tracking the tally per $(X, Y)$ coordinate. If a coordinate has fewer than 4 selected teams, we dispatch a team. If it reaches 4, we skip it. This guarantees strict adherence to the prompt rules and stops exactly at 25.

---

## Robustness Analysis

### 1. Handling Extreme Splits (Worst-Split NDCG@25)
XGBoost is heavily regularized (`max_depth=4`, `colsample_bytree=0.8`, `subsample=0.8`, `learning_rate=0.05`) to prevent overfitting to the specific training split. This ensures that even if an evaluation split has an unusual distribution of high-impact fires, the model does not collapse, maintaining a stable worst-split NDCG@25.

### 2. Generalization to Outliers
The logarithmic transformation of the target variable ($\log(1+\text{area})$) heavily dampens the effect of extreme outliers in the training set. A single massive fire of 1000 hectares won't skew the gradient updates disproportionately compared to a 10-hectare fire, making the model more robust to extreme variance in unseen data.

### 3. Edge Cases in Constraint Satisfaction
The greedy algorithm runs in $O(N \log N)$ time due to sorting, ensuring the runtime is well within the required limits (under a few seconds). It robustly handles coordinate counting using a dictionary, ensuring no memory overhead issues regardless of the dataset size.
