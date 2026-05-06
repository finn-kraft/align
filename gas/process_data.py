import pandas as pd
import os

# ----------------------------
# PATHS (module-local)
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(BASE_DIR, "data", "live_data.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "processed_data.csv")


def main():
    if not os.path.exists(INPUT_FILE):
        print("⚠️ No input file found")
        return

    try:
        df = pd.read_csv(INPUT_FILE)

        # ----------------------------
        # TYPE SAFETY (critical fix)
        # ----------------------------
        numeric_cols = ["Odometer", "Gallons", "Total Cost"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ----------------------------
        # CLEANING
        # ----------------------------
        df = df.dropna(subset=["Odometer", "Gallons"])
        df = df.sort_values("Odometer").reset_index(drop=True)

        # ----------------------------
        # DERIVED METRICS
        # ----------------------------
        df["MilesPerTank"] = df["Odometer"].diff()

        # avoid divide-by-zero
        df["TripMPG"] = df["MilesPerTank"] / df["Gallons"]
        df["TripMPG_clean"] = df["TripMPG"].clip(15, 40)

        df["RollingMPG_mean"] = (
            df["TripMPG_clean"]
            .rolling(window=5, min_periods=1)
            .mean()
        )

        # ----------------------------
        # TIMESTAMP
        # ----------------------------
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        else:
            df["Timestamp"] = pd.Timestamp.now()

        df["Month"] = df["Timestamp"].dt.to_period("M").astype(str)
        df["Year"] = df["Timestamp"].dt.year

        # ----------------------------
        # COST METRICS
        # ----------------------------
        df["PricePerGallon"] = df["Total Cost"] / df["Gallons"]
        df["CostPerMile"] = df["Total Cost"] / df["MilesPerTank"]

        df["CostPerMile_MA10"] = (
            df["CostPerMile"]
            .rolling(window=10, min_periods=2)
            .mean()
        )

        # ----------------------------
        # FINAL CLEAN
        # ----------------------------
        df = df.replace([float("inf"), -float("inf")], pd.NA)
        df = df.dropna(subset=["MilesPerTank", "TripMPG", "CostPerMile"])

        # ----------------------------
        # SAFE WRITE (critical)
        # ----------------------------
        tmp_file = OUTPUT_FILE + ".tmp"
        df.to_csv(tmp_file, index=False)
        os.replace(tmp_file, OUTPUT_FILE)

        # ----------------------------
        # SUMMARY (optional)
        # ----------------------------
        summary = {
            "Mean MPG": df["TripMPG_clean"].mean(),
            "Total Miles": df["MilesPerTank"].sum(),
            "Total Cost": df["Total Cost"].sum(),
            "Avg Cost/Mile": df["CostPerMile"].mean(),
        }

        print("\n--- GAS SUMMARY ---")
        for k, v in summary.items():
            print(f"{k:18}: {v:.3f}")

        print(f"\n✅ Saved → {OUTPUT_FILE}")

    except Exception as e:
        print("❌ Processing error:", e)


if __name__ == "__main__":
    main()