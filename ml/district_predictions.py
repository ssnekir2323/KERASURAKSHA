import pandas as pd

from risk_model import predict_risk


# =========================================================
# KERASURAKSHA AI DISTRICT PREDICTIONS
# =========================================================

DATA_FILE = "data/disaster_training_data.csv"

OUTPUT_FILE = "data/ai_district_risk.csv"


# =========================================================
# LOAD DATA
# =========================================================

data = pd.read_csv(DATA_FILE)


print()
print("========================================")
print(" KERASURAKSHA AI DISTRICT RISK")
print("========================================")
print()

print(
    f"Processing {len(data)} districts..."
)

print()


# =========================================================
# GENERATE AI PREDICTIONS
# =========================================================

predictions = []


for _, row in data.iterrows():

    result = predict_risk(

        rainfall_mm=row["rainfall_mm"],

        elevation_m=row["elevation_m"],

        slope_degree=row["slope_degree"],

        river_distance_km=row["river_distance_km"],

        historical_risk=row["historical_risk"]

    )


    predictions.append({

        "district":
            row["district"],

        "rainfall_mm":
            row["rainfall_mm"],

        "elevation_m":
            row["elevation_m"],

        "slope_degree":
            row["slope_degree"],

        "river_distance_km":
            row["river_distance_km"],

        "historical_risk":
            row["historical_risk"],

        "ai_risk_score":
            result["risk_score"],

        "ai_risk_level":
            result["risk_level"]

    })


# =========================================================
# CREATE OUTPUT DATAFRAME
# =========================================================

output = pd.DataFrame(
    predictions
)


# =========================================================
# SORT BY HIGHEST RISK
# =========================================================

output = output.sort_values(

    by="ai_risk_score",

    ascending=False

)


# =========================================================
# SAVE RESULTS
# =========================================================

output.to_csv(

    OUTPUT_FILE,

    index=False

)


# =========================================================
# DISPLAY RESULTS
# =========================================================

print("AI District Predictions")
print("-----------------------")

for _, row in output.iterrows():

    print(

        f'{row["district"]}: '

        f'{row["ai_risk_score"]} '

        f'({row["ai_risk_level"]})'

    )


print()

print(
    "AI district predictions saved to:"
)

print(
    OUTPUT_FILE
)

print()

print("========================================")
print(" AI DISTRICT MAP DATA READY")
print("========================================")