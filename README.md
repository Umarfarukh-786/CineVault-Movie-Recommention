# CineVault — Movie Recommendation Engine 🎬🍿

CineVault is an intelligent, data-driven movie recommendation web application. Built using Python, machine learning, and web development technologies, the system analyzes user viewing patterns and film characteristics to deliver highly accurate, personalized entertainment recommendations. The platform bridges data science with robust backend APIs to create a seamless, responsive end-user experience.

---

## 🚀 Key Features

- **Personalized Recommendations:** Employs advanced machine learning algorithms (Content-Based and Collaborative Filtering) to suggest films matching specific user tastes.
- **Dynamic Content Search:** A responsive, live search engine allowing users to explore thousands of titles instantaneously.
- **Asynchronous Movie Discovery:** Uses client-side JavaScript combined with custom internal APIs to load film metadata, genres, and ratings without frustrating page reloads.
- **Rich Media Delivery:** Fetches high-quality metadata, movie posters, and synopses dynamically via JSON data exchange payloads from upstream entertainment microservices.

---

## 🛠️ Tech Stack & System Architecture

CineVault is engineered to showcase a modern machine learning workflow integrated into a fully functional web platform:

*   **Machine Learning & Data Analysis:** Python, Pandas, NumPy, Scikit-learn (Feature extraction, Cosine Similarity matrices, TF-IDF vectorization)
*   **Backend Application Layer:** Python Web Framework (Django/Flask) managing clean internal Web APIs
*   **Data Interchange Format:** Standardized **JSON** payloads used for API request-response handling between the model backend and the UI
*   **Frontend Interface:** Interactive JavaScript (ES6+), HTML5, and CSS3 for real-time client-side rendering

---

## 📊 Machine Learning Workflow

The underlying engine processes film data through a rigorous engineering pipeline before serving predictions:

[ Raw Movie Dataset ]
|
v
[ Data Cleaning & Preprocessing ] (Handling missing values, parsing JSON genres/keywords)
|
v
[ Text Vectorization ] (Applying TF-IDF / CountVectorizer on text features)
|
v
[ Similarity Matrix ] (Computing Cosine Similarity scores across the vector space)
|
v
[ REST/Web API Layer ] ---> Exposes top-K recommendations to the JavaScript frontend


---

## ⚡ API Endpoints (Recommendation Delivery)

| Method | Endpoint | Description | Expected Payload / Response |
| :--- | :--- | :--- | :--- |
| **POST / GET** | `/api/recommend/` | Accepts a target movie title and returns top recommended films | `JSON` array of recommended movie objects |
| **GET** | `/api/movies/search?q=` | Queries the dataset for live auto-complete search matching | Predictive `JSON` text titles array |

---

## 💻 Installation & Setup

Follow these steps to run CineVault locally on your machine:

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Clone the Repository
bash
git clone [https://github.com/Umarfarukh-786/CineVault-Movie-Recommention.git](https://github.com/Umarfarukh-786/CineVault-Movie-Recommention.git)
cd CineVault-Movie-Recommention
3. Setup Virtual Environment & Dependencies
Bash
# Create environment
python -m venv venv

# Activate environment (Windows)
venv\Scripts\activate

# Activate environment (Mac/Linux)
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
4. Process the Recommendation Matrices (If required)
If your model requires pre-computed similarity weights or vector pickles, execute the pipeline script:

Bash
python processing_pipeline.py
5. Launch the Web Application
Bash
python app.py  # or python manage.py runserver depending on framework setup
Open your web browser and navigate to http://127.0.0.1:5000/ (or port 8000) to test the engine.

📈 Future Roadmap / Scalability Focus
[ ] Hybrid Recommendation Model: Combine content features with collaborative user matrix factorization (SVD) for enhanced predictive accuracy.

[ ] Live Third-Party API Integration: Transition from local metadata stores to live, asynchronous TMDB Web API fetches for up-to-the-minute poster and trailer delivery.

[ ] User Authentication: Add persistent profile tracking to allow users to build custom watchlist databases.
