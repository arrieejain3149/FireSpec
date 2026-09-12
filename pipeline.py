import argparse
import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import ndcg_score
from sklearn.model_selection import KFold
import logging
import warnings

warnings.filterwarnings('ignore')

# ---------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("IGNIS_PIPELINE")

# ---------------------------------------------------------
# MODULE 1: Spatial Graph & Physics Feature Engine
# ---------------------------------------------------------
def build_spatial_physics_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["drying_pressure"] = data["temp"] / (data["RH"] + 1.0)
    data["kinetic_spread"] = data["ISI"] * data["wind"]
    
    grid_fuel = data.groupby(["X", "Y"])["DC"].mean().to_dict()
    
    unique_coords = data[["X", "Y"]].drop_duplicates()
    coord_risk_map = {}
    for _, row in unique_coords.iterrows():
        x, y = row["X"], row["Y"]
        accum = 0.0
        count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                neighbor = (x + dx, y + dy)
                if neighbor in grid_fuel:
                    accum += grid_fuel[neighbor]
                    count += 1
        coord_risk_map[(x, y)] = accum / count if count > 0 else grid_fuel.get((x, y), 0)
        
    coords = zip(data["X"].values, data["Y"].values)
    # Fallback to the row's own DC if needed (handled inside zip map)
    dc_vals = data["DC"].values
    data["spatial_neighborhood_dc"] = [coord_risk_map.get(c, dc) for c, dc in zip(coords, dc_vals)]
    
    features = [
        "X", "Y", "FFMC", "DMC", "DC", "ISI", "temp", "RH", "wind", "rain",
        "drying_pressure", "kinetic_spread", "spatial_neighborhood_dc"
    ]
    return data[features]

# ---------------------------------------------------------
# MODULE 2: Asymmetric Risk Estimator (Base Model)
# ---------------------------------------------------------
class OperationalRiskEstimator:
    def __init__(self, seed: int = 42):
        self.scaler = StandardScaler()
        self.active_clf = GradientBoostingClassifier(
            n_estimators=70, max_depth=3, learning_rate=0.05, random_state=seed
        )
        self.severity_reg = GradientBoostingRegressor(
            loss="quantile", alpha=0.85, n_estimators=80, max_depth=3,
            learning_rate=0.05, random_state=seed
        )

    def fit(self, X_train: pd.DataFrame, y_area: np.ndarray):
        X_feats = build_spatial_physics_features(X_train)
        X_scaled = self.scaler.fit_transform(X_feats)
        is_active = (y_area > 0).astype(int)
        self.active_clf.fit(X_scaled, is_active)
        y_log = np.log1p(y_area)
        self.severity_reg.fit(X_scaled, y_log)

    def estimate_hazard(self, X_eval: pd.DataFrame) -> np.ndarray:
        X_feats = build_spatial_physics_features(X_eval)
        X_scaled = self.scaler.transform(X_feats)
        p_active = self.active_clf.predict_proba(X_scaled)[:, 1]
        q85_severity = np.maximum(0.0, self.severity_reg.predict(X_scaled))
        return p_active * (q85_severity + 0.1)

# ---------------------------------------------------------
# MODULE 3: Risk Ensemble (The Unbreakable Core)
# ---------------------------------------------------------
class RiskEnsemble:
    def __init__(self, n_models=5):
        self.n_models = n_models
        self.models = [OperationalRiskEstimator(seed=42 + i) for i in range(n_models)]
        logger.info(f"Initialized RiskEnsemble with {n_models} independent estimators.")

    def fit(self, X_train: pd.DataFrame, y_area: np.ndarray):
        logger.info("Training ensemble models...")
        for i, model in enumerate(self.models):
            model.fit(X_train, y_area)
        logger.info("Ensemble training complete.")

    def estimate_hazard(self, X_eval: pd.DataFrame) -> np.ndarray:
        preds = [model.estimate_hazard(X_eval) for model in self.models]
        return np.mean(preds, axis=0)

    def get_feature_importances(self) -> np.ndarray:
        # Average the feature importances of the active_clf models
        imps = [m.active_clf.feature_importances_ for m in self.models]
        return np.mean(imps, axis=0)

# ---------------------------------------------------------
# MODULE 4: Constrained Dispatch Solver (ILP)
# ---------------------------------------------------------
def solve_optimal_dispatch(df: pd.DataFrame, hazard_scores: np.ndarray, k: int = 25, max_per_cell: int = 4):
    df = df.reset_index(drop=True)
    n = len(df)
    k = min(k, n)
    c = -hazard_scores
    
    from scipy.sparse import vstack, csr_matrix, lil_matrix
    
    # Total allocation constraint
    A_eq = csr_matrix(np.ones((1, n)))
    b_eq_low = np.array([k])
    b_eq_high = np.array([k])
    
    # Spatial boundary constraints
    cell_groups = df.groupby(["X", "Y"]).groups
    num_cells = len(cell_groups)
    
    A_cells_lil = lil_matrix((num_cells, n))
    for row_idx, (_, group_indices) in enumerate(cell_groups.items()):
        A_cells_lil[row_idx, list(group_indices)] = 1.0
        
    b_cells_low = np.zeros(num_cells)
    b_cells_high = np.full(num_cells, max_per_cell)
    
    A_total = vstack([A_eq, A_cells_lil.tocsr()])
    lhs = np.concatenate([b_eq_low, b_cells_low])
    rhs = np.concatenate([b_eq_high, b_cells_high])
    
    constraints = LinearConstraint(A_total, lhs, rhs)
    integrality = np.ones(n)
    bounds = Bounds(0, 1)
    
    logger.info("Solving Integer Linear Program for optimal dispatch...")
    # Safe limits: 5.0 seconds maximum
    res = milp(c=c, integrality=integrality, constraints=constraints, bounds=bounds, 
               options={'time_limit': 5.0})
    
    if res.success:
        logger.info("ILP Solved to mathematical optimality.")
        return np.round(res.x).astype(int)
    else:
        logger.warning(f"ILP solver hit limits ({res.status}). Falling back to greedy heuristic.")
        sorted_idx = np.argsort(-hazard_scores)
        z_opt = np.zeros(n, dtype=int)
        counts = {}
        for idx in sorted_idx:
            cell = (df.iloc[idx]["X"], df.iloc[idx]["Y"])
            if counts.get(cell, 0) < max_per_cell:
                z_opt[idx] = 1
                counts[cell] = counts.get(cell, 0) + 1
            if np.sum(z_opt) == k:
                break
        return z_opt

# ---------------------------------------------------------
# MODULE 5: Local Explainability Engine
# ---------------------------------------------------------
def generate_justifications(df: pd.DataFrame, portfolio: np.ndarray, ensemble: RiskEnsemble, hazard_scores: np.ndarray, output_csv: str):
    logger.info("Generating explainability justifications for dispatch decisions...")
    
    # Extract only dispatched rows
    dispatched_idx = np.where(portfolio == 1)[0]
    dispatched_df = df.iloc[dispatched_idx].copy().reset_index(drop=True)
    dispatched_hazard = hazard_scores[dispatched_idx]
    
    feats_df = build_spatial_physics_features(dispatched_df)
    feature_names = feats_df.columns.tolist()
    global_importances = ensemble.get_feature_importances()
    
    # Normalize features to 0-1 across the dataset to fairly multiply by global importance
    full_feats_df = build_spatial_physics_features(df)
    scaler = StandardScaler().fit(full_feats_df)
    feats_scaled = scaler.transform(feats_df)
    
    justifications = []
    for i in range(len(dispatched_df)):
        # Approximate local attribution: normalized feature value * global feature importance
        local_contributions = np.abs(feats_scaled[i]) * global_importances
        top_feat_idx = np.argmax(local_contributions)
        top_feat_name = feature_names[top_feat_idx]
        
        row_x = dispatched_df.iloc[i]["X"]
        row_y = dispatched_df.iloc[i]["Y"]
        row_month = dispatched_df.iloc[i]["month"]
        
        reason = f"Top risk driver: {top_feat_name} (Standardized Magnitude: {np.abs(feats_scaled[i][top_feat_idx]):.2f})"
        justifications.append({
            "Location_X": row_x,
            "Location_Y": row_y,
            "Month": row_month,
            "Hazard_Score": f"{dispatched_hazard[i]:.4f}",
            "Primary_Justification": reason
        })
        
    just_df = pd.DataFrame(justifications).sort_values(by="Hazard_Score", ascending=False)
    just_df.to_csv(output_csv, index=False)
    logger.info(f"Justifications saved to {output_csv}")


# ---------------------------------------------------------
# MODULE 6: Cross-Validation & Entrypoint
# ---------------------------------------------------------
def evaluate_splits(df: pd.DataFrame):
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    ndcgs, recalls = [], []
    for fold, (train_idx, val_idx) in enumerate(kf.split(df)):
        logger.info(f"--- Evaluating Fold {fold+1} ---")
        tr, val = df.iloc[train_idx], df.iloc[val_idx]
        model = RiskEnsemble(n_models=5)
        model.fit(tr, tr["area"].values)
        scores = model.estimate_hazard(val)
        sel = solve_optimal_dispatch(val, scores)
        
        k_eval = min(25, len(val_idx))
        ndcg = ndcg_score([val["area"].values], [scores], k=k_eval)
        ndcgs.append(ndcg)
        
        p80 = np.percentile(tr["area"].values, 80, method="linear")
        hi = val["area"].values >= p80
        recall = np.sum((sel == 1) & hi) / np.sum(hi) if np.sum(hi) > 0 else 1.0
        recalls.append(recall)
        
        logger.info(f"Fold {fold+1} Metrics -> NDCG@25: {ndcg:.4f}, Recall@25: {recall:.4f}")
        
    logger.info(f"Final Validation Result -> Mean NDCG@25: {np.mean(ndcgs):.4f} | Worst-Split: {np.min(ndcgs):.4f} | Recall: {np.mean(recalls):.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_csv", default="data/forestfires.csv")
    parser.add_argument("--eval_csv", default=None)
    parser.add_argument("--output_csv", default="submission.csv")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    logger.info("Initializing IGNIS Operational Dispatch Engine...")
    train_df = pd.read_csv(args.train_csv)
    
    if args.validate:
        evaluate_splits(train_df)
    else:
        eval_df = pd.read_csv(args.eval_csv) if args.eval_csv else train_df.drop(columns=["area"], errors="ignore")
        
        ensemble = RiskEnsemble(n_models=5)
        ensemble.fit(train_df, train_df["area"].values)
        scores = ensemble.estimate_hazard(eval_df)
        portfolio = solve_optimal_dispatch(eval_df, scores)
        
        # 1. Output Submission
        pd.DataFrame({"impact_score": scores, "selected_for_response": portfolio}).to_csv(args.output_csv, index=False)
        logger.info(f"Submission generated successfully: {args.output_csv}")
        
        # 2. Output Explanations
        generate_justifications(eval_df, portfolio, ensemble, scores, "dispatch_justifications.csv")
        logger.info("Pipeline execution completed flawlessly.")
