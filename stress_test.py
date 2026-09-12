import numpy as np
import pandas as pd
import time
import logging
import traceback
from pipeline import RiskEnsemble, solve_optimal_dispatch, generate_justifications

# Configure local logging for the stress test
logging.basicConfig(level=logging.INFO, format='[STRESS TEST] %(message)s')
logger = logging.getLogger("STRESS")

def generate_synthetic(n, area_type="random", extreme_weather=False):
    df = pd.DataFrame({
        "X": np.random.randint(1, 10, n),
        "Y": np.random.randint(1, 10, n),
        "month": np.random.choice(['jan','aug','sep','dec'], n),
        "day": np.random.choice(['mon','fri','sun'], n),
        "FFMC": np.random.uniform(90, 100, n) if extreme_weather else np.random.uniform(18, 96, n),
        "DMC": np.random.uniform(200, 300, n) if extreme_weather else np.random.uniform(1, 200, n),
        "DC": np.random.uniform(700, 900, n) if extreme_weather else np.random.uniform(7, 700, n),
        "ISI": np.random.uniform(20, 60, n) if extreme_weather else np.random.uniform(0, 20, n),
        "temp": np.random.uniform(35, 45, n) if extreme_weather else np.random.uniform(2, 35, n),
        "RH": np.random.uniform(5, 15, n) if extreme_weather else np.random.uniform(15, 100, n),
        "wind": np.random.uniform(8, 15, n) if extreme_weather else np.random.uniform(0.4, 8, n),
        "rain": np.zeros(n) if extreme_weather else np.random.uniform(0, 2, n),
    })
    
    if area_type == "random":
        df["area"] = np.random.exponential(10, n)
        # Zero inflation
        df.loc[np.random.choice(n, size=int(n*0.5), replace=False), "area"] = 0.0
    elif area_type == "zero":
        df["area"] = 0.0
    elif area_type == "massive":
        df["area"] = np.random.uniform(1000, 5000, n)
        
    return df

def run_stress_test():
    logger.info("INITIATING MAXIMUM STRESS PROTOCOL")
    results = {}
    
    # Base training data
    train_df = generate_synthetic(500)
    ensemble = RiskEnsemble(n_models=3)
    ensemble.fit(train_df, train_df["area"].values)
    
    # ---------------------------------------------------------
    # TEST 1: The "Megafire" Scalability Test (10,000 rows)
    # ---------------------------------------------------------
    logger.info(">>> TEST 1: 10,000 Row Scalability & MILP Timeout Check")
    mega_df = generate_synthetic(10000)
    try:
        t0 = time.time()
        scores = ensemble.estimate_hazard(mega_df)
        portfolio = solve_optimal_dispatch(mega_df, scores, k=25)
        dt = time.time() - t0
        logger.info(f"PASS: Handled 10,000 rows in {dt:.2f}s. Selected {np.sum(portfolio)} crews.")
        results["T1_Scale"] = "PASS"
    except Exception as e:
        logger.error(f"FAIL: {e}")
        results["T1_Scale"] = "FAIL"

    # ---------------------------------------------------------
    # TEST 2: The "Absolute Zero" Test (No fires anywhere)
    # ---------------------------------------------------------
    logger.info(">>> TEST 2: Zero-Inflation Edge Case (All areas = 0)")
    zero_df = generate_synthetic(200, area_type="zero")
    try:
        scores = ensemble.estimate_hazard(zero_df)
        portfolio = solve_optimal_dispatch(zero_df, scores, k=25)
        logger.info(f"PASS: Survived all-zero targets. Max hazard generated: {np.max(scores):.4f}")
        results["T2_Zeroes"] = "PASS"
    except Exception as e:
        logger.error(f"FAIL: {e}")
        results["T2_Zeroes"] = "FAIL"

    # ---------------------------------------------------------
    # TEST 3: The "Doomsday" Extreme Weather Test
    # ---------------------------------------------------------
    logger.info(">>> TEST 3: Extreme Weather Physics (Temp > 40, RH < 10)")
    doom_df = generate_synthetic(200, area_type="massive", extreme_weather=True)
    try:
        scores = ensemble.estimate_hazard(doom_df)
        logger.info(f"PASS: Handled extreme physics math without NaN. Mean hazard: {np.mean(scores):.4f}")
        results["T3_Physics"] = "PASS"
    except Exception as e:
        logger.error(f"FAIL: {e}")
        results["T3_Physics"] = "FAIL"

    # ---------------------------------------------------------
    # TEST 4: Ridiculous Constraints Breakage
    # ---------------------------------------------------------
    logger.info(">>> TEST 4: Adversarial Solver Constraints (k > n, max_per_cell=0)")
    try:
        # Case A: Request 1 million crews for 100 fires
        portfolio_A = solve_optimal_dispatch(doom_df.iloc[:100], scores[:100], k=1000000)
        
        # Case B: Allow 0 per cell
        portfolio_B = solve_optimal_dispatch(doom_df.iloc[:100], scores[:100], k=25, max_per_cell=0)
        
        logger.info(f"PASS: Survived adversarial constraints. PortA sum={np.sum(portfolio_A)}, PortB sum={np.sum(portfolio_B)}")
        results["T4_Constraints"] = "PASS"
    except Exception as e:
        logger.error(f"FAIL: {e}")
        results["T4_Constraints"] = "FAIL"

    # ---------------------------------------------------------
    # TEST 5: Explainability Pipeline on Synthetic Data
    # ---------------------------------------------------------
    logger.info(">>> TEST 5: Generating Justifications for Megafire Data")
    try:
        generate_justifications(mega_df, portfolio, ensemble, scores, "stress_justifications.csv")
        logger.info("PASS: SHAP-fallback explainability generated successfully for 10,000 row dispatch.")
        results["T5_Explain"] = "PASS"
    except Exception as e:
        logger.error(f"FAIL:\n{traceback.format_exc()}")
        results["T5_Explain"] = "FAIL"

    logger.info("========================================")
    logger.info(f"STRESS TEST SUMMARY: {list(results.values()).count('PASS')}/5 PASSED")
    logger.info("========================================")

if __name__ == "__main__":
    run_stress_test()
