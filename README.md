# 🏆 LaLiga Match Outcome Predictor

A sophisticated football prediction engine that leverages a multi-model stacking ensemble to predict match outcomes (Home Win, Draw, Away Win) with high precision and calibration. This system is specifically tuned for LaLiga, incorporating real-time data, historical team performance, and injury impacts.

## 🤖 Prediction Algorithms

The system uses a **Stacked Generalization (Stacking Ensemble)** architecture, which combines the strengths of statistical models and machine learning classifiers.

### 1. Dixon-Coles Poisson Model
A refined version of the classic Poisson distribution for football modeling.
- **Function**: Predicts goals for each team as independent Poisson variables.
- **Dixon-Coles Adjustment**: Solves the "low-score dependency" problem where 0-0 and 1-1 results occur more frequently than independent Poisson models suggest.
- **Time-Decay**: Uses a half-life weighting system where recent matches have a stronger influence on the team's attack and defense parameters than older matches.
- **Parameters**: Extracts latent "Attack Strength" and "Defense Strength" for every team in LaLiga via Maximum Likelihood Estimation (MLE).

### 2. Gradient Boosting (XGBoost & LightGBM)
High-performance tree-based models that capture non-linear relationships.
- **Features Engine**: Processes Elo ratings, rolling Points Per Game (PPG), Expected Goals (xG) proxies, and Head-to-Head win rates.
- **XGBoost**: Focuses on regularization and handling sparse data to prevent overfitting to specific season anomalies.
- **LightGBM**: Efficiently handles large historical datasets with leaf-wise growth, often picking up subtle form trends that XGBoost might miss.

### 3. Random Forest
An ensemble of decision trees that provides robustness.
- **Function**: Uses bagging and feature randomness to reduce variance. It serves as a stable "anchor" in the ensemble, ensuring that outliers in recent form don't disproportionately skew the prediction.

### 4. Stacking Ensemble Engine (The Meta-Learner)
The core of the prediction logic.
- **Meta-Learner**: A **Logistic Regression** model trained on the "Out-of-Fold" (OOF) probability predictions of the base models (Poisson, XGB, LGBM, RF).
- **Synergy**: Instead of just averaging models, the meta-learner learns *when* to trust the Dixon-Coles model (e.g., for low-scoring defensive teams) vs *when* to trust XGBoost (e.g., when form momentum is high).

### 5. Probability Calibration
- Uses **Isotonic Regression** to ensure "probabilistic truth." If the model predicts a 60% probability for a Home Win, that outcome should occur in exactly 60% of cases over a large sample, making the output reliable for risk assessment.

---

## 🛠️ Technical Stack

### **Backend (Python)**
- **Framework**: Python 3.x
- **ML Libraries**: `xgboost`, `lightgbm`, `scikit-learn`, `pandas`, `numpy`, `scipy`
- **Database**: SQLite with `SQLAlchemy` ORM for storing match history and predictions.
- **Data Acquisition**: Custom scrapers and integration with `API-Football` (RapidAPI).

### **Frontend (React)**
- **Core**: Vite, TypeScript, React 18
- **UI Components**: shadcn/ui, Lucid-React (icons)
- **Styling**: Tailwind CSS
- **Visualization**: Dynamic progress bars and probability charts for match outcomes.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- An API-Football key (if fetching live data)

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Configure your `.env` with `RAPIDAPI_KEY`.
4. Run the prediction engine:
   ```bash
   python main.py
   ```

### Frontend Setup
1. Navigate to the root directory:
   ```bash
   npm install
   ```
2. Start the development server:
   ```bash
   npm run dev
   ```

---

## 📊 Data Features
The models are trained on several key feature categories:
- **Form Stats**: Rolling 5-game PPG, goal averages, and defensive stability.
- **Metric Deltas**: The difference in Elo and xG between the home and away sides.
- **Contextual Factors**: Days since the last match (fatigue) and key player injury reports.
- **H2H**: Historical dominance between the two specific clubs.

---

## ⚖️ Disclaimer
This project is for educational and analytical purposes only. Match predictions are probabilistic and do not guarantee outcomes.
