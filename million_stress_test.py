import numpy as np
import pandas as pd
import time
import logging
import os
from pipeline import RiskEnsemble, solve_optimal_dispatch

# Configure local logging for the million-row stress test
logging.basicConfig(level=logging.INFO, format='[1M STRESS] %(message)s')
logger = logging.getLogger("1M_STRESS")

def generate_million_rows():
    n = 1_000_000
    logger.info(f"Generating {n} synthetic rows (realistic distribution)...")
    
    # 60% Summer, 20% Winter, 20% Spring/Fall
    seasons = np.random.choice(['summer', 'winter', 'shoulder'], n, p=[0.6, 0.2, 0.2])
    
    # Base features
    df = pd.DataFrame({
        "X": np.random.randint(1, 10, n),
        "Y": np.random.randint(1, 10, n),
        "day": np.random.choice(['mon','tue','wed','thu','fri','sat','sun'], n),
    })
    
    # Months mapped to seasons roughly
    summer_idx = seasons == 'summer'
    winter_idx = seasons == 'winter'
    shoulder_idx = seasons == 'shoulder'
    
    months = np.empty(n, dtype=object)
    months[summer_idx] = np.random.choice(['jun','jul','aug','sep'], np.sum(summer_idx))
    months[winter_idx] = np.random.choice(['dec','jan','feb'], np.sum(winter_idx))
    months[shoulder_idx] = np.random.choice(['mar','apr','may','oct','nov'], np.sum(shoulder_idx))
    df["month"] = months
    
    # Temp
    temp = np.zeros(n)
    temp[summer_idx] = np.random.uniform(25, 45, np.sum(summer_idx))
    temp[winter_idx] = np.random.uniform(0, 15, np.sum(winter_idx))
    temp[shoulder_idx] = np.random.uniform(10, 25, np.sum(shoulder_idx))
    df["temp"] = temp
    
    # RH
    rh = np.zeros(n)
    rh[summer_idx] = np.random.uniform(10, 40, np.sum(summer_idx))
    rh[winter_idx] = np.random.uniform(40, 100, np.sum(winter_idx))
    rh[shoulder_idx] = np.random.uniform(30, 70, np.sum(shoulder_idx))
    df["RH"] = rh
    
    df["FFMC"] = np.random.uniform(18, 100, n)
    df["DMC"] = np.random.uniform(1, 300, n)
    df["DC"] = np.random.uniform(7, 900, n)
    df["ISI"] = np.random.uniform(0, 60, n)
    df["wind"] = np.random.uniform(0.4, 15, n)
    df["rain"] = np.random.uniform(0, 10, n)
    
    # Area - Zero-inflated long tail
    area = np.random.exponential(10, n)
    zero_mask = np.random.rand(n) < 0.6  # 60% zeroes
    area[zero_mask] = 0.0
    df["area"] = area
    
    mem_usage = df.memory_usage(deep=True).sum() / 1024**2
    logger.info(f"Dataset generated. Size in memory: {mem_usage:.2f} MB")
    
    return df

def run_million_stress():
    # 1. Train on a standard batch
    train_df = pd.read_csv("data/forestfires.csv")
    ensemble = RiskEnsemble(n_models=3)
    logger.info("Training ensemble on historical dataset...")
    ensemble.fit(train_df, train_df["area"].values)
    
    # 2. Generate 1M
    mega_df = generate_million_rows()
    
    # 3. Inference
    logger.info("Starting Hazard Inference on 1,000,000 rows...")
    t0 = time.time()
    scores = ensemble.estimate_hazard(mega_df)
    t_infer = time.time() - t0
    logger.info(f"Inference complete in {t_infer:.2f} seconds.")
    
    # 4. Dispatch solver
    logger.info("Starting ILP Dispatch Optimization on 1,000,000 constraints...")
    t1 = time.time()
    portfolio = solve_optimal_dispatch(mega_df, scores, k=25, max_per_cell=4)
    t_solve = time.time() - t1
    logger.info(f"Dispatch optimization complete in {t_solve:.2f} seconds.")
    
    print("="*50)
    print(f"Total Inference Time : {t_infer:.2f} seconds")
    print(f"Total ILP Solve Time : {t_solve:.2f} seconds")
    print(f"Total Dispatched     : {np.sum(portfolio)} crews")
    print(f"Mean Hazard Score    : {np.mean(scores):.4f}")
    print(f"Max Hazard Score     : {np.max(scores):.4f}")
    print("="*50)

if __name__ == "__main__":
    run_million_stress()
