# Stock Trading Simulator

This is a Flask-based web application that simulates a stock trading environment. Users can register, log in, manage a virtual portfolio, trade stocks and cryptocurrencies, and earn badges for various achievements.

## Features

* **User Authentication:** Secure registration and login system.
* **Virtual Portfolio:** Users start with a virtual balance and can buy/sell stocks and cryptocurrencies.
* **Real-Time Data:** Fetches stock and crypto data from external APIs (Finnhub, CoinGecko, yfinance).
* **Trading Simulation:** Simulates trade execution and updates user balances.
* **Badges and Achievements:** Users earn badges for reaching milestones and demonstrating trading skills.
* **Customizable UI:** Users can customize the color scheme of their interface.
* **Error Logging:** Detailed logging to help diagnose issues.
* **Caching:** Implements Redis caching to reduce API calls and improve performance.
* **Asynchronous Tasks:** Uses Celery with Redis as a message broker to handle background tasks.

## Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.7+:** [https://www.python.org/downloads/](https://www.python.org/downloads/)
* **pip:** Python package installer (usually comes with Python).
* **Redis:** In-memory data structure store (used as Celery broker and cache). [https://redis.io/download](https://redis.io/download)
* **Google Cloud SDK (gcloud):** Required for interacting with Google Cloud services (Firestore, Logging). [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

## Setup and Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/Buraisu-tiu/Stock-trading-sim.git
    cd Stock-trading-sim
    ```

2. **Create a virtual environment:**

    ```sh
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3. **Install dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Configure Google Cloud:**

    * **Create a Google Cloud Project:** If you don't already have one, create a project in the Google Cloud Console: [https://console.cloud.google.com/](https://console.cloud.google.com/)
    * **Enable Firestore and Cloud Logging:** Enable these services for your project in the Google Cloud Console.
    * **Create a Service Account:** Create a service account with the necessary permissions (Firestore read/write, Cloud Logging write).
    * **Download the Service Account Key:** Download the JSON key file for your service account.
    * **Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable:**

        ```sh
        export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"  # Replace with the actual path
        ```

        (You might want to add this to your `.bashrc` or `.zshrc` file for persistence.)
    * **Set the Project ID:**

        ```sh
        export GOOGLE_CLOUD_PROJECT="your-project-id" # Replace with your Google Cloud Project ID
        ```

5. **Configure API Keys:**

    This application uses several financial APIs to get real-time stock data. You'll need to set up API keys to get the best experience.

    ### Option 1: Environment Variables (Recommended for Production)

    Set the following environment variables:

    ```bash
    export FINNHUB_API_KEY=your_finnhub_api_key
    export ALPHA_VANTAGE_KEY=your_alpha_vantage_api_key
    ```

    ### Option 2: Local Development File

    1. Create a file called `api_keys.py` in the `src` directory
    2. Add your API keys:

    ```python
    FINNHUB_API_KEY = 'your_finnhub_api_key'
    ALPHA_VANTAGE_KEY = 'your_alpha_vantage_api_key'
    ```

    ### Getting API Keys

    - **Finnhub**: Sign up at [Finnhub.io](https://finnhub.io/) for a free API key
    - **Alpha Vantage**: Get a free API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key)

6. **Configure Flask Secret Key:**

    * Set a strong, random secret key for your Flask application:

        ```sh
        export FLASK_SECRET_KEY="your_secret_key"  # Replace with a strong, random key
        ```

7. **Start Redis:**

    ```sh
    redis-server
    ```

8. **Start Celery Worker:**

    ```sh
    celery -A app.celery worker --loglevel=info
    ```

    (Replace `app` with the name of your Flask application file if it's different.)

9. **Run the Flask Application:**

    ```sh
    flask run  # Or `python app.py` if using a standalone script
    ```

    (Make sure you are in the virtual environment.)

10. **Access the application:**

    Open your web browser and go to `http://127.0.0.1:5000/` (or the address shown in the Flask output).

## Configuration

The following environment variables are used:

* `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google Cloud service account key file.
* `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID.
* `FLASK_SECRET_KEY`: Your Flask application's secret key.
* `REDIS_URL`: Redis server URL (default is `redis://localhost:6379/0`).
* `CELERY_BROKER_URL`: URL for Celery message broker (default is `redis://localhost:6379/0`).
* `CELERY_RESULT_BACKEND`: Backend for Celery task results (default is `redis://localhost:6379/0`).

## Important Considerations

* **Security:** This application is a simplified simulation and may not implement all necessary security measures for a production environment. Be especially careful when handling user data and API keys.
* **API Usage:** Be mindful of the API usage limits for the external data providers you are using (Finnhub, CoinGecko, etc.). Implement caching and error handling to avoid exceeding these limits.
* **Error Handling:** The application includes basic error logging, but you should implement more robust error handling and monitoring for a production environment.
* **Data Accuracy:** The accuracy of the simulated trading environment depends on the real-time data provided by the external APIs. These APIs may have occasional outages or data inaccuracies.
* **Scalability:** For a production environment, consider using a more scalable database (e.g., PostgreSQL) and deploying the application using a platform like Google Cloud Run or Kubernetes.

## Troubleshooting API Issues

If you encounter API errors:

1. Verify your API keys are correct
2. Check rate limits - free tiers have limited API calls
3. Consider upgrading to premium API tiers for production use
4. The application will fall back to alternative data sources if one fails

## Contributing

Contributions are welcome! Please submit pull requests with bug fixes, new features, or improvements to the documentation.

## License
MIT License

Copyright (c) 2025 Bryce K Tieu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

