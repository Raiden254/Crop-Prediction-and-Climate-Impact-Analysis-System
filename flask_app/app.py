from flask import Flask, render_template, url_for, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import os
import io
from io import StringIO
import pandas as pd
import plotly.express as px
import json


app = Flask(__name__)
app.secret_key = "@ce1824"

#--- Database Setup ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///submissions.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.Float, nullable=False)
    actual_yield = db.Column(db.Float, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

#-- Admin credentials--
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "root2025"

# Load data once
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
METRICS_FILE = os.path.join(DATA_DIR, "all_metrics.json")
with open(METRICS_FILE, "r") as f:
    all_metrics = json.load(f)

def load_csv(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if filename == "horticulture.csv":
        # Special handling for malformed horticulture.csv
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Parse the quoted CSV lines
        data = []
        for line in lines:
            line = line.strip()
            if line.startswith('"') and line.endswith('"'):
                # Remove quotes and split by comma
                content = line[1:-1]
                data.append(content.split(','))
            else:
                data.append(line.split(','))
        # Convert to DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])  # First row is header
        return df
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            cleaned = "\n".join(
                line[1:-1] if line.startswith('"') and line.endswith('"') else line
                for line in (ln.strip() for ln in f)
            )
        return pd.read_csv(StringIO(cleaned))

DATA_FILE = os.path.join(DATA_DIR, "combined_data.csv")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

# strip outer quotes and clean each line
cleaned_lines = []
for line in lines:
    line = line.strip()
    if line.startswith('"') and line.endswith('"'):
        line = line[1:-1]          # remove outer quotes
    line = line.replace('""', '"') # fix escaped inner quotes like ""Beans, dry""
    cleaned_lines.append(line)

cleaned = "\n".join(cleaned_lines)
df = pd.read_csv(StringIO(cleaned), index_col=0)
df.columns = df.columns.str.strip()
df["Crop"] = df["Crop"].str.strip()

# rename crops to match your model keys
df["Crop"] = df["Crop"].str.strip()
CROP_NAME_MAP = {
    "Maize (corn)":  "Maize",
    "Beans, dry":    "Beans",
    "Sugar cane":    "SugarCane",
    "Tea leaves":    "Tea",
}
df["Crop"] = df["Crop"].replace(CROP_NAME_MAP)


climate_df = load_csv("Climate.csv")

BACKGROUND_IMAGE_FILENAMES = {
    "overview": "overview.jpg",
    "climate": "climate.jpg",
    "maize": "maize.jpg",
    "beans": "beans.jpg",
    "potatoes": "potatoes.jpg",
    "sorghum": "sorghum.jpg",
    "millet": "millet.jpg",
    "wheat": "wheat.jpg",
    "sugarcane": "sugarcane.jpg",
    "tea": "tea.jpg",
    "rice":       "rice.jpg",
    "cabbages":    "cabbage.jpg",
    "coffee, green":     "coffee.jpg",
    "mangoes, guavas and mangosteens":    "mangoes.jpg",
    "tomatoes":   "tomatoes.jpg",
    "bananas":    "bananas.jpg",
    "avocados":    "avocado.jpg",
    "oranges":    "oranges.jpg",
    "onions and shallots, dry (excluding dehydrated)":     "onions.jpg",
    "pineapples": "pineapple.jpg",
    "carrots and turnips":    "carrots.jpg",
    "predict": "predict image 1.jpg",
    "admin_dashboard": "predict image 2.jpg",
    "admin_login": "predict image 2.jpg"
}

def get_background_image(crop_key):
    print(f"Getting background image for crop key: {crop_key}")
    filename = BACKGROUND_IMAGE_FILENAMES.get(crop_key, "maize.jpg")
    return url_for("static", filename=f"images/{filename}")

@app.route("/")
def overview():
    crops = df["Crop"].unique()
    current_crop = "overview"

    rain_fig = px.line(df, x="Year", y="Rainfall", title="Rainfall Trend")
    temp_fig = px.line(df, x="Year", y="Temperature", title="Temperature Trend")
    yield_fig = px.line(df, x="Year", y="Production", facet_col="Crop",
                        facet_col_wrap=3, title="Crop Yield Trends by Crop")
    yield_fig.update_yaxes(type="log")
    rain_yield = px.scatter(df, x="Rainfall", y="Production", color="Crop",
                            title="Rainfall vs Crop Yield")
    rain_yield.update_yaxes(type="log")
    temp_yield = px.scatter(df, x="Temperature", y="Production", color="Crop",
                            title="Temperature vs Crop Yield")
    temp_yield.update_yaxes(type="log")

    background_image = get_background_image(current_crop)
    return render_template(
        "overview.html",
        crops=crops,
        current_crop="overview",
        background_image=background_image,
        rain_chart=rain_fig.to_html(full_html=False),
        temp_chart=temp_fig.to_html(full_html=False),
        yield_chart=yield_fig.to_html(full_html=False),
        rain_yield_chart=rain_yield.to_html(full_html=False),
        temp_yield_chart=temp_yield.to_html(full_html=False)
    )

@app.route("/climate")
def climate():

    crops = df["Crop"].unique()
    current_crop = "climate"          # for overview

    # --- Climate Trends ---
    rain_fig = px.line(climate_df, x="Year", y="prcp", title="Rainfall Trend", markers=True)
    temp_fig = px.line(climate_df, x="Year", y=["tavg", "tmin", "tmax"], title="Temperature Trends", markers=True)    

    # --- Production Trends ---
   
    range_fig = px.line(climate_df, x="Year", y="temp_range", title="Temperature Variability", markers=True)
    
    # --- Relationships ---
    wind_fig = px.line(climate_df, x="Year", y="wspd", title="Wind Speed Trend", markers=True)

    pressure_fig = px.line(climate_df, x="Year", y="pres", title="Atmospheric Pressure Trend", markers=True)

    # --- Additional Plots ---
    rain_hist = px.histogram(climate_df, x="prcp", title="Rainfall Distribution")
    corr_matrix = climate_df.corr()
    corr_heatmap = px.imshow(corr_matrix, text_auto=".2f", title="Correlation Heatmap", color_continuous_scale="rdbu")


    
    background_image = get_background_image(current_crop)
    return render_template(
        "climate.html",
        crops=crops,
        current_crop="climate",
        background_image=background_image,
        temp_chart=temp_fig.to_html(full_html=False),
        rain_chart=rain_fig.to_html(full_html=False),
        range_chart=range_fig.to_html(full_html=False),
        wind_chart=wind_fig.to_html(full_html=False),
        pressure_chart=pressure_fig.to_html(full_html=False),
        rain_hist_chart=rain_hist.to_html(full_html=False),
        corr_heatmap_chart=corr_heatmap.to_html(full_html=False)
        )

@app.route("/crop/<crop_name>")
def crop_page(crop_name):
    crops = df["Crop"].unique()
    
    current_crop = crop_name.lower()
    df_crop = df[df["Crop"].str.lower() == current_crop]

    if df_crop.empty:
        return f"Crop '{crop_name.capitalize()}' not found.", 404

    # ── Automatic insights ────────────────────────────────────
    avg_production = df_crop["Production"].mean()
    rain_corr = df_crop["Rainfall"].corr(df_crop["Production"])
    temp_corr = df_crop["Temperature"].corr(df_crop["Production"])

    if avg_production > 50000:
        production_insight = f"{crop_name.capitalize()} has a high average production, indicating it is a major crop in the region."
    else:
        production_insight = f"{crop_name.capitalize()} has a relatively low average production, suggesting it may be a minor crop or more sensitive to environmental factors."

    if rain_corr > 0.5:
        rain_insight = f"Strong positive correlation between rainfall and {crop_name} production — higher rainfall tends to increase yields."
    elif rain_corr > 0:
        rain_insight = f"Weak positive correlation between rainfall and {crop_name} production — rainfall has some influence but other factors matter more."
    elif rain_corr < -0.5:
        rain_insight = f"Strong negative correlation between rainfall and {crop_name} production — higher rainfall may decrease yields, possibly due to waterlogging."
    elif rain_corr < 0:
        rain_insight = f"Weak negative correlation between rainfall and {crop_name} production — excessive rainfall may have some negative impact."
    else:
        rain_insight = f"No significant correlation between rainfall and {crop_name} production."

    if temp_corr > 0.5:
        temp_insight = f"Strong positive correlation between temperature and {crop_name} production — warmer temperatures tend to increase yields."
    elif temp_corr > 0:
        temp_insight = f"Weak positive correlation between temperature and {crop_name} production — temperature has some influence but other factors matter more."
    elif temp_corr < -0.5:
        temp_insight = f"Strong negative correlation between temperature and {crop_name} production — higher temperatures may decrease yields due to heat stress."
    elif temp_corr < 0:
        temp_insight = f"Weak negative correlation between temperature and {crop_name} production — higher temperatures may have some negative impact."
    else:
        temp_insight = f"No significant correlation between temperature and {crop_name} production."

    background_image = get_background_image(current_crop)

    yield_fig = px.line(df_crop, x="Year", y="Production",
                        title=f"{crop_name.capitalize()} Yield Trend")
    rain_yield = px.scatter(df_crop, x="Rainfall", y="Production",
                            title=f"{crop_name.capitalize()} Rainfall vs Yield")
    temp_yield = px.scatter(df_crop, x="Temperature", y="Production",
                            title=f"{crop_name.capitalize()} Temperature vs Yield")
    heatmap = px.density_heatmap(df_crop, x="Rainfall", y="Temperature", z="Production",
                                 title=f"{crop_name.capitalize()} Yield Heatmap",
                                 color_continuous_scale="Viridis")

    return render_template(
        "crop.html",
        crop_name=crop_name.capitalize(),
        current_crop=current_crop,
        crops=crops,
        background_image=background_image,
        yield_chart=yield_fig.to_html(full_html=False),
        rain_yield_chart=rain_yield.to_html(full_html=False),
        temp_yield_chart=temp_yield.to_html(full_html=False),
        heatmap_chart=heatmap.to_html(full_html=False),
        production_insight=production_insight,
        rain_insight=rain_insight,
        temp_insight=temp_insight
    )

import requests

@app.route("/predict", methods=["GET", "POST"])
def predict():

    crops = df["Crop"].unique()
    prediction = None
    error = None

    if request.method == "POST":
        crop = request.form["crop"]
        model = request.form["model"]
        rainfall = float(request.form["rainfall"])
        temperature = float(request.form["temperature"])
        actual_yield = request.form.get("actual_yield")
        actual_yield = float(actual_yield) if actual_yield else None
        if crop.lower() == "horticulture":
            crop = "hort"

        payload = {
            "crop": crop,
            "model": model,
            "features": [rainfall, temperature]
        }

        try:
            FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
            response = requests.post(f"{FASTAPI_URL}/predict", json=payload)            
            result = response.json()

            if "prediction" in result:
                prediction = result["prediction"]
                submission = Submission(
                    crop=crop,
                    model=model,
                    rainfall=rainfall,
                    temperature=temperature,
                    prediction=prediction,
                    actual_yield=actual_yield,
                    submitted_at=datetime.utcnow()
                )
                db.session.add(submission)
                db.session.commit()

            else:
                error = result.get("error", "Unknown error")

        except Exception as e:
            error = str(e)

   
    return render_template(
        "predict.html",
        crops=crops,
        prediction=prediction,
        error=error,
        current_crop="predict",
        all_metrics=json.dumps(all_metrics),
        background_image = get_background_image("predict")   
    )
@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = None
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USERNAME and
                request.form.get("password") == ADMIN_PASSWORD):
            session["admin_logged_in"] = True
            return redirect("/admin/dashboard")
        error = "Invalid credentials"

    return render_template("admin_login.html", error=error,
                           background_image = get_background_image("admin_login")
                 )

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin")

#-- Admin Dashboard --
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin")

    submissions = Submission.query.order_by(Submission.submitted_at.desc()).all()
    return render_template("admin_dashboard.html", submissions=submissions,
                           background_image = get_background_image("admin_dashboard") 
                        )

#-- Export Submissions as CSV --
@app.route("/admin/export")
def admin_export():
    if not session.get("admin_logged_in"):
        return redirect("/admin")

    submissions = Submission.query.order_by(Submission.submitted_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Crop", "Model", "Rainfall", "Temperature", "Prediction", "Actual Yield", "Submitted At"])
    for s in submissions:
        writer.writerow([s.id, s.crop, s.model, s.rainfall, s.temperature, s.prediction, s.actual_yield, s.submitted_at])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="submissions.csv"
    )
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)