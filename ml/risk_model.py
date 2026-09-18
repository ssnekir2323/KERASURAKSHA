import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error


# =========================================================
# KERASURAKSHA AI RISK PREDICTION MODEL
# =========================================================

DATA_FILE = "data/disaster_training_data.csv"


# =========================================================
# LOAD DATA
# =========================================================

data = pd.read_csv(DATA_FILE)

print()
print("========================================")
print(" KERASURAKSHA AI RISK PREDICTION")
print("========================================")
print()

print("Training data loaded:")
print(f"{len(data)} locations found.")
print()


# =========================================================
# FEATURES
# =========================================================

features = [
    "rainfall_mm",
    "elevation_m",
    "slope_degree",
    "river_distance_km",
    "historical_risk"
]

X = data[features]

y = data["risk_score"]


# =========================================================
# TRAIN / TEST DATA
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


# =========================================================
# CREATE RANDOM FOREST MODEL
# =========================================================

model = RandomForestRegressor(
    n_estimators=200,
    random_state=42
)


# =========================================================
# TRAIN MODEL
# =========================================================

print("Training AI model...")

model.fit(
    X_train,
    y_train
)

print("Training completed.")
print()


# =========================================================
# TEST MODEL
# =========================================================

predictions = model.predict(X_test)

error = mean_absolute_error(
    y_test,
    predictions
)


print("Model Performance")
print("-----------------")

print(
    f"Mean Absolute Error: {error:.2f}"
)

print()


# =========================================================
# RISK LEVEL
# =========================================================

def get_risk_level(score):

    if score < 30:

        return "Low"

    elif score < 50:

        return "Moderate"

    elif score < 75:

        return "High"

    else:

        return "Critical"


# =========================================================
# PREDICT DISASTER RISK
# =========================================================

def predict_risk(
    rainfall_mm,
    elevation_m,
    slope_degree,
    river_distance_km,
    historical_risk
):

    input_data = pd.DataFrame(
        [[
            rainfall_mm,
            elevation_m,
            slope_degree,
            river_distance_km,
            historical_risk
        ]],
        columns=features
    )


    prediction = model.predict(
        input_data
    )


    score = float(
        prediction[0]
    )


    # Keep score between 0 and 100

    score = max(
        0,
        min(100, score)
    )


    level = get_risk_level(
        score
    )


    return {
        "risk_score": round(score, 2),
        "risk_level": level
    }


# =========================================================
# TEST PREDICTION
# =========================================================

if __name__ == "__main__":

    print("Example Prediction")
    print("------------------")


    result = predict_risk(

        rainfall_mm=250,

        elevation_m=50,

        slope_degree=18,

        river_distance_km=1.5,

        historical_risk=70

    )


    print(
        "Rainfall:",
        "250 mm"
    )

    print(
        "Elevation:",
        "50 m"
    )

    print(
        "Slope:",
        "18 degrees"
    )

    print(
        "River Distance:",
        "1.5 km"
    )

    print(
        "Historical Risk:",
        "70"
    )

    print()


    print(
        "AI Risk Score:",
        result["risk_score"]
    )

    print(
        "AI Risk Level:",
        result["risk_level"]
    )


    print()
    print("========================================")
    print(" AI PREDICTION ENGINE IS WORKING")
    print("========================================")