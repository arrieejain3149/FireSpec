import numpy as np
import pandas as pd
import time
import logging
from pipeline import RiskEnsemble, solve_optimal_dispatch

# Configure local logging
logging.basicConfig(level=logging.INFO, format='[100M STRESS] %(message)s')
logger = logging.getLogger("100M_STRESS")

def generate_100_million_rows():
    n = 100_000_000
    logger.info(f"Allocating {n} synthetic rows directly to float32 to conserve RAM...")
    
    # We will build this efficiently to avoid python overhead memory spikes
    # Random uniform generation directly into float32
    df = pd.DataFrame({
        "X": np.random.randint(1, 10, size=n, dtype=np.int8),
        "Y": np.random.randint(1, 10, size=n, dtype=np.int8),
        "month": np.random.choice(['jun','jul','aug','sep','oct','dec'], n),
        "day": np.random.choice(['mon','fri','sun'], n),
        "temp": np.random.uniform(5, 45, n).astype(np.float32),
        "RH": np.random.uniform(10, 100, n).astype(np.float32),
        "FFMC": np.random.uniform(18, 100, n).astype(np.float32),
        "DMC": np.random.uniform(1, 300, n).astype(np.float32),
        "DC": np.random.uniform(7, 900, n).astype(np.float32),
        "ISI": np.random.uniform(0, 60, n).astype(np.float32),
        "wind": np.random.uniform(0.4, 15, n).astype(np.float32),
        "rain": np.random.uniform(0, 10, n).astype(np.float32),
    })
    
    area = np.random.exponential(10, n).astype(np.float32)
    zero_mask = np.random.rand(n) < 0.6
    area[zero_mask] = 0.0
    df["area"] = area
    
    mem_usage = df.memory_usage(deep=True).sum() / 1024**3
    logger.info(f"Dataset generated perfectly. Size in memory: {mem_usage:.2f} GB")
    
    return df

def run_100m_stress():
    train_df = pd.read_csv("data/forestfires.csv")
    ensemble = RiskEnsemble(n_models=3)
    logger.info("Training ensemble on historical dataset...")
    ensemble.fit(train_df, train_df["area"].values)
    
    mega_df = generate_100_million_rows()
    
    logger.info("Starting Hazard Inference on 100,000,000 rows...")
    t0 = time.time()
    scores = ensemble.estimate_hazard(mega_df)
    t_infer = time.time() - t0
    logger.info(f"Inference complete in {t_infer:.2f} seconds.")
    
    logger.info("Starting ILP Dispatch Optimization on 100,000,000 constraints...")
    t1 = time.time()
    portfolio = solve_optimal_dispatch(mega_df, scores, k=25, max_per_cell=4)
    t_solve = time.time() - t1
    logger.info(f"Dispatch optimization complete in {t_solve:.2f} seconds.")
    
    print("\n" + "="*50)
    print("100 MILLION ROW STRESS TEST REPORT")
    print("="*50)
    print(f"Total Inference Time : {t_infer:.2f} seconds")
    print(f"Total ILP Solve Time : {t_solve:.2f} seconds")
    print(f"Total Dispatched     : {np.sum(portfolio)} crews")
    print(f"Mean Hazard Score    : {np.mean(scores):.4f}")
    print(f"Max Hazard Score     : {np.max(scores):.4f}")
    print("="*50)

if __name__ == "__main__":
    run_100m_stress()
