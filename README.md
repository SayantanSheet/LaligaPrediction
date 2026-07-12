# 🏆 LaLiga Match Outcome Predictor & Stacking Ensemble Pipeline

A state-of-the-art football prediction system engineered with a multi-model stacking ensemble framework specifically optimized for LaLiga. The platform couples statistical goal-generation models with gradient-boosted decision trees and random forests to forecast match outcomes (Home Win, Draw, Away Win) and exact scorelines. The pipeline features strict temporal-safety barriers (zero data leakage), out-of-fold stacking, and isotonic probability calibration.

---

## 📌 Project Overview
Predicting association football matches is famously complex due to low-scoring dynamics, high draws variance, and volatile home advantages. This project implements a robust machine learning and statistical modeling pipeline that:
1. **Ingests historical match data** containing goals, ELO ratings, and team details.
2. **Engineers rolling performance and fatigue profiles** without forward-looking data leakage.
3. **Trains a 4-model base ensemble** involving Poisson processes and tree-based classifiers.
4. **Feeds out-of-fold base predictions** combined with game contexts into a meta-learner (XGBoost or Logistic Regression).
5. **Calibrates win/draw/loss probabilities** via Isotonic Regression to ensure probability declarations match real-world long-term frequencies.
6. **Exposes predictions via a FastAPI backend** backed by an SQLite database.
7. **Serves an elite frontend dashboard** built on Vite, React, Shadcn UI, Tailwind CSS, and Recharts.

---

## 🧱 System Architecture & Workflow

The end-to-end data pipeline is structured to extract data, build features, train base/meta models, calibrate, and serve predictions:

```mermaid
flowchart TD
    subgraph Data Layer
        A[APIFootballFetcher / RapidAPI] -->|fetch_fixtures| B[JSON Raw Data: matches-all-seasons.json]
        C[player_data.py] -->|Mock player database & injuries| D[Key Player Impacts & Injuries]
    end

    subgraph Feature Engineering (Zero Leakage)
        B -->|load & sort| E[Preprocessing & Outcome Coding]
        E -->|Rolling Window = 5| F[Shifted Features: PPG, Roll GS, Roll GA, GD]
        F -->|Differential Calculation| G[Elo Difference, PPG Delta, Form Slopes]
    end

    subgraph Training Pipeline (5-Fold Walk-Forward Split)
        G -->|Walk-Forward Time Series Split| H[Training folds / Validation folds]
        H -->|Fit Base Model 1| I[Dixon-Coles Poisson Model]
        H -->|Fit Base Model 2| J[Random Forest Classifier]
        H -->|Fit Base Model 3| K[XGBoost Classifier]
        H -->|Fit Base Model 4| L[LightGBM Classifier]
    end

    subgraph Stacking Ensemble (Meta-Learning)
        I & J & K & L -->|Out-of-Fold Probabilities| M[OOF Prediction Matrix 12 Cols]
        G -->|PPG Gap & Elo Diff| N[Context Features 3 Cols]
        M --> O[Meta Input Matrix 15 Cols]
        N --> O
        O -->|Compare LogReg vs XGBoost| P{Metric Benchmarking}
        P -->|Lowest LogLoss / RPS| Q[Meta-Learner Classifier]
    end

    subgraph Calibration & Output
        Q -->|Calibration Held-out Split 20%| R[Isotonic Regression Calibration]
        R -->|Calibrated Outputs| S[Final Probabilities: H / D / A]
        I -->|Simulated Bivariate Poisson| T[Most Likely exact Scoreline]
    end

    subgraph Service & Interface
        S & T & D --> U[FastAPI Endpoint: /api/predict]
        V[SQLite predictions.db] --> U
        U -->|JSON Payload| W[React Frontend Dashboard]
    end
```

---

## 🤖 Prediction Algorithms Breakdown

### 1. Dixon-Coles Poisson Model (`poisson_model.py`)
Standard Poisson models treat goals scored by the Home ($h$) and Away ($a$) teams as independent events; however, this underestimates draws in low-scoring football matches. The Dixon-Coles Poisson model solves this using a bivariate Poisson distribution with an independence/low-score correction factor.

* **Goal Distributions**:
  $$X_i \sim \text{Poisson}(\lambda_i), \quad Y_i \sim \text{Poisson}(\mu_i)$$
  $$\lambda_i = \exp(\text{att}_{\text{home}} + \text{def}_{\text{away}} + \gamma)$$
  $$\mu_i = \exp(\text{att}_{\text{away}} + \text{def}_{\text{home}})$$
  Where:
  * $\text{att}_t$ and $\text{def}_t$ are the attack and defense parameters estimated for each team.
  * $\gamma$ is the league-wide home field advantage parameter.

* **Low-Score Draw Correction ($\rho$)**:
  Allows adjustment for scorelines $(0,0), (1,0), (0,1),$ and $(1,1)$ via a dependency connection:
  $$\tau(x, y) = \begin{cases} 
    1 - \lambda \mu \rho & \text{if } x=0, y=0 \\
    1 + \mu \rho & \text{if } x=1, y=0 \\
    1 + \lambda \rho & \text{if } x=0, y=1 \\
    1 - \rho & \text{if } x=1, y=1 \\
    1.0 & \text{otherwise}
  \end{cases}$$

* **Time-Decay Metric weighting ($\tau$)**:
  Recent matches reflect current form better than historical matches. Attack and defense parameters are estimated by maximizing a weighted log-likelihood:
  $$w(t) = \exp\left(-\frac{\ln(2) \cdot \Delta t}{\lambda_{\text{half-life}}}\right)$$
  * **Tuned Parameter**: Tested dynamically via TimeSeries split sweeps; set to **90 days** (optimized for LaLiga dynamics, avoiding overfitting of 60-day limits).

---

### 2. Gradient Boosting Tree Models (`football_predictor_xgb.py` & `football_ensemble.py`)
Tree classifiers excel at finding non-linear relationships and thresholds (e.g. how a 250-point ELO gap interacts with injury reports).

* **XGBoost (Extreme Gradient Boosting)**: Corrects residual errors of preceding trees sequentially. Utilizes severe L1/L2 regularization via `reg_alpha` and `reg_lambda` to prevent overfitting.
* **LightGBM (Light Gradient Boosting Machine)**: Utilizes leaf-wise growth rather than level-wise growth to discover deeper relationships in form metrics and delta parameters.

---

### 3. Random Forest Classifier (`rf_model.py` & `football_ensemble.py`)
* Acts as a bagging-based stabilizing classifier. Bagging builds trees on random bootstrap samples and averages predictions, reducing prediction variance.
* **Balanced Weights**: Uses balanced sample weights ($w_j = \frac{N}{C \times n_j}$) to counteract drawing infrequency.

---

### 4. Probability Calibration
Statistical classifiers can be over-confident (e.g., predicting a $90\%$ win chance when empirical performance is only $70\%$). 
* The pipeline separates a chronological **20% held-out calibration dataset** from the training partition.
* Applies **Isotonic Regression** (via `CalibratedClassifierCV`) on the base models' logits, guaranteeing that predicting a probability $P$ leads to outcome success $P$ in historical evaluations.

---

## 🧬 Model Assembly & Stacking Logic
The pipeline uses **Stacked Generalization** (Stacking) to pool prediction capabilities:

1. **Feature Engineering**: For every fixture in the history:
   * Form statistics (rolling 5-game points-per-game, rolling goals scored, rolling goals conceded) are calculated.
   * Features are strictly **shifted by 1** (`.shift(1)`) to ensure the training rows only possess data that was true *before* kickoff (zero leakage).
   * Team name strings are encoded using `category_encoders.OrdinalEncoder`. Unseen teams are mapped to `0` (a neutral prior) to prevent training/evaluation crashes.
2. **Timeline Splits**: The system splits historical fixtures using **Walk-Forward Time-Series Split** (5 folds) with a minimum training data ceiling of 150 matches to secure statistical estimators.
3. **Out-of-Fold (OOF) Prediction Matrix**:
   * For each split, base models (Poisson, XGBoost, LGBM, Random Forest) are trained on the training partition.
   * Base models predict probabilities on the validation partition. This yields a validation OOF prediction matrix:
     $$\mathbf{X}_{\text{OOF}} = [\mathbf{P}_{\text{Poisson}}, \mathbf{P}_{\text{RF}}, \mathbf{P}_{\text{XGB}}, \mathbf{P}_{\text{LGBM}}] \in \mathbb{R}^{V \times 12}$$
4. **Context Enrichment**:
   * The OOF matrix is combined with contextual match metadata: ELO differences and rolling PPG statistics.
     $$\mathbf{X}_{\text{Meta}} = [\mathbf{X}_{\text{OOF}}, \Delta\text{ELO}, \text{PPG}_{\text{home}}, \text{PPG}_{\text{away}}] \in \mathbb{R}^{V \times 15}$$
5. **Meta-Learner Training & Benchmark Selection**:
   * During training, candidates for the meta-learner (an XGBoost Classifier and a Logistic Regression Classifier) are dynamically benchmarked on validation splits.
   * The model displaying the lowest Ranked Probability Score (RPS) and Log Loss is automatically selected as the final meta-learner.
   * The final meta-learner, base models, and Isotonic Calibrators are fitted to the entire dataset to maximize prediction accuracy for future matches.

---

## 📂 Project Structure

```
LaligaPrediction-project/
├── backend/
│   ├── api_football_fetcher.py      # Requests fixtures from API-Football
│   ├── database.py                  # SQLite configuration & SQLAlchemy Schemas
│   ├── football_ensemble.py         # Stacking ensemble engine & walk-forward splits
│   ├── football_predictor_xgb.py    # Independent XGBoost/LightGBM model pipeline
│   ├── main.py                      # FastAPI App definition & local routes
│   ├── player_data.py               # Player index & injury simulation (15% random chance)
│   ├── poisson_model.py             # Dixon-Coles goal/score forecasting & parameter fitting
│   ├── predictor.py                 # PredictionEngine class tying models & mocks together
│   ├── requirements.txt             # Backend python packages
│   └── rf_model.py                  # Random Forest Classifier baseline
├── frontend/
│   ├── src/
│   │   ├── components/              # Shadcn components (Dialog, Select, Progress, etc)
│   │   ├── App.tsx                  # Main entry point & React dashboard view
│   │   └── index.css                # Styling overrides
│   ├── package.json                 # Node package configuration
│   ├── postcss.config.js            # PostCSS settings
│   ├── tailwind.config.ts           # Tailwind parameters
│   └── vite.config.ts               # Vite bundler options
├── src/
│   └── data/
│       └── matches-all-seasons.json # Canonical match dataset JSON repository
├── evaluate_pipeline.py             # Execution script to run validation sweeps
└── README.md                        # Master Project Documentation
```

---

## 🛠️ Technical Stack & Requirements

### **Backend (Python)**
* Python 3.10+
* **Core Libraries**: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `requests`, `python-dotenv`, `pandas`, `scipy`, `numpy`
* **ML Stack**: `scikit-learn`, `xgboost`, `lightgbm`, `category-encoders`
* **Scraper Stack**: `beautifulsoup4`, `lxml`

### **Frontend (Vite + React)**
* Vite 5, React 18, TypeScript
* **UI toolkit**: shadcn/ui, Tailwind CSS, Lucide React
* **Charts**: Recharts (for distribution curves, calibration, and prediction weights)

---

## 🚀 Installation & Build Procedures

### Step 1: Clone and Configure Environment
Create a `.env` file in the `backend/` directory:
```bash
# In LaligaPrediction-project/backend/.env
API_FOOTBALL_KEY=your_rapidapi_football_key_here
```
> [!NOTE]
> If `API_FOOTBALL_KEY` is not provided, the scraper will fail, but the backend automatically falls back to synthetic match generation inside testing tools and utilizes cached JSON resources.

---

### Step 2: Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the data scraper setup (Optional: only needed if you have a valid RapidAPI Key):
   ```bash
   python scraper.py
   ```
   *This saves match profiles to `src/data/matches-all-seasons.json`.*
5. Run the final validation checks to test pipeline accuracy:
   ```bash
   python test_ensemble.py
   ```

---

### Step 3: Start the Backend server
Run the FastAPI developer server:
```bash
python main.py
```
By default, the backend will bind to `http://localhost:8000`.

---

### Step 4: Frontend Installation
1. Open a new terminal and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Initialize the frontend development server:
   ```bash
   npm run dev
   ```
By default, Vite will serve the project layout on `http://localhost:5173`.

---

## 📋 API Reference Summary

The FastAPI app exposes endpoints for predictions and database updates:

| Endpoint | Method | Description | Body / Parameters |
|:---|:---|:---|:---|
| `/api/teams` | `GET` | Fetches a sorted list of all unique teams currently present in the dataset. | None |
| `/api/predict` | `POST` | Assembles prediction inputs, runs the ensemble stacking engine, logs results to database, and outputs JSON metrics. | `{"home_team": "Real Madrid", "away_team": "Barcelona"}` |
| `/api/history` | `GET` | Pulls the last 20 queries from the SQLite prediction logs (`predictions.db`). | None |
| `/api/refresh` | `POST` | Triggers the scrape pipeline in `scraper.py` and prompts the model to retrain on updated records. | None |

### `/api/predict` Response JSON Example
```json
{
  "home_team": "Real Madrid",
  "away_team": "Barcelona",
  "predicted_score": "2-1",
  "probabilities": {
    "home_win": 0.524,
    "draw": 0.231,
    "away_win": 0.245
  },
  "poisson_probs": {
    "home": 51.2,
    "draw": 24.1,
    "away": 24.7
  },
  "rf_probs": {
    "home": 49.8,
    "draw": 26.2,
    "away": 24.0
  },
  "confidence": 52.4,
  "comparison": {
    "agreement": "MEDIUM",
    "variance": 1.2,
    "recommendation": "Ensemble Optimized Prediction"
  },
  "market_analysis": {
    "over_1_5": 84.5,
    "over_2_5": 54.2,
    "btts": 56.1
  },
  "performance_analysis": {
    "home": {
      "avg_scored": 1.9,
      "avg_conceded": 0.9,
      "played": 76,
      "strength": "STRONG",
      "lambda": 1.84
    },
    "away": {
      "avg_scored": 1.6,
      "avg_conceded": 1.1,
      "played": 76,
      "strength": "STRONG",
      "lambda": 1.21
    }
  },
  "form_analysis": {
    "home": {
      "match_history": [
        {"date": "2023-11-04", "opponent": "Valencia", "outcome": "Win", "score": "5-1"}
      ],
      "points": 12,
      "label": "GOOD FORM"
    },
    ...
  },
  "player_impact": {
    "home_key_player": {
      "top_scorer": "Jude Bellingham",
      "goals": 16,
      "key_injured": false
    },
    "away_key_player": {
      "top_scorer": "Robert Lewandowski",
      "goals": 14,
      "key_injured": false
    },
    "home_injured": false,
    "away_injured": false,
    "insight": "Full squad available for key players."
  },
  "h2h_history": [
    {
      "id": 1032900,
      "homeTeam": "Real Madrid",
      "awayTeam": "Barcelona",
      "homeScore": 2,
      "awayScore": 1,
      "date": "2023-10-28",
      "season": 2023
    }
  ]
}
```

---

## 📈 Model Verification & Sweeps

To run the backtests and verify predictions against historical records, you can execute the benchmarking script:
```bash
python evaluate_pipeline.py
```
This script calls cross-validation splits and evaluates:
1. **RPS (Ranked Probability Score)**: Represents the deviation of prediction vectors from actual outcomes.
2. **Log Loss (Cross-Entropy Loss)**: Measures certainty errors.
3. **Macro-average F1 Score**: Ensures performance balance across Home, Draw, and Away outputs.
4. **Draw Recall**: Proves model resilience against the hardest outcomes to predict.

---

## ⚖️ Disclaimer
This project is for educational and analytical purposes. Match predictions generated by the ensemble are entirely probabilistic and do not guarantee final sports outcomes or betting success. Use responsibly.
