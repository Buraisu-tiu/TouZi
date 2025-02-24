# Stock Trading Simulator

This is a Flask-based web application that simulates a stock trading environment. Users can register, log in, manage a virtual portfolio, trade stocks and cryptocurrencies, and earn badges for various achievements.

## Features

*   **User Authentication:** Secure registration and login system.
*   **Virtual Portfolio:**  Users start with a virtual balance and can buy/sell stocks and cryptocurrencies.
*   **Real-Time Data:** Fetches stock and crypto data from external APIs (Finnhub, CoinGecko, yfinance).
*   **Trading Simulation:**  Simulates trade execution and updates user balances.
*   **Badges and Achievements:** Users earn badges for reaching milestones and demonstrating trading skills.
*   **Customizable UI:** Users can customize the color scheme of their interface.
*   **Error Logging:**  Detailed logging to help diagnose issues.
*   **Caching:** Implements caching to reduce API calls and improve performance.
*   **Asynchronous Tasks:** Uses Celery for handling background tasks.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.7+:**  [https://www.python.org/downloads/](https://www.python.org/downloads/)
*   **pip:** Python package installer (usually comes with Python).
*   **Redis:**  In-memory data structure store (used as Celery broker and cache).  [https://redis.io/download](https://redis.io/download)
*   **Google Cloud SDK (gcloud):** Required for interacting with Google Cloud services (Firestore, Logging). [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

## Setup and Installation

1.  **Clone the repository:**

    ```
    git clone https://github.com/Buraisu-tiu/Stock-trading-sim.git
    ```

2.  **Create a virtual environment:**

    ```
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```
    pip install -r requirements.txt
    ```

4.  **Configure Google Cloud:**

    *   **Create a Google Cloud Project:** If you don't already have one, create a project in the Google Cloud Console: [https://console.cloud.google.com/](https://console.cloud.google.com/)
    *   **Enable Firestore and Cloud Logging:**  Enable these services for your project in the Google Cloud Console.
    *   **Create a Service Account:** Create a service account with the necessary permissions (Firestore read/write, Cloud Logging write).
    *   **Download the Service Account Key:** Download the JSON key file for your service account.
    *   **Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable:**

        ```
        export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"  # Replace with the actual path
        ```

        (You might want to add this to your `.bashrc` or `.zshrc` file for persistence.)
    *   **Set the Project ID:**

        ```
        export GOOGLE_CLOUD_PROJECT="your-project-id" # Replace with your Google Cloud Project ID
        ```

5.  **Configure API Keys:**

    *   Obtain API keys from Finnhub, Coinbase, and any other data providers you plan to use.
    *   Replace the placeholder values in the code (e.g., `'your_coinbase_api_key'`, `'ctitlv1r01qgfbsvh1dgctitlv1r01qgfbsvh1e0'`) with your actual API keys.
    *   **Important:** Store your API keys securely.  Do not commit them directly to your repository.  Consider using environment variables or a secrets management system.

6.  **Configure Flask Secret Key:**

    *   Set a strong, random secret key for your Flask application:

        ```
        app.secret_key = 'your_secret_key'  # Replace with a strong, random key
        ```

        *   **Important:**  Do not use a simple or easily guessable secret key.  Generate a strong, random key and store it securely.

7.  **Start Redis:**

    ```
    redis-server
    ```

8.  **Start Celery Worker:**

    ```
    celery -A app.celery worker -l info
    ```

    (Replace `app` with the name of your Flask application file if it's different.)

9.  **Run the Flask Application:**

    ```
    python app.py  # Or the name of your main application file
    ```

    (Make sure you are in the virtual environment.)

10. **Access the application:**

    Open your web browser and go to `http://127.0.0.1:5000/` (or the address shown in the Flask output).

## Configuration

The following environment variables are used:

*   `GOOGLE_APPLICATION_CREDENTIALS`:  Path to your Google Cloud service account key file.
*   `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID.

The following settings are configured directly in the `app.py` file:

*   API Keys (Finnhub, Coinbase, etc.)
*   Flask Secret Key
*   Redis broker URL (`redis://localhost:6379/0`)

## Important Considerations

*   **Security:** This application is a simplified simulation and may not implement all necessary security measures for a production environment.  Be especially careful when handling user data and API keys.
*   **API Usage:**  Be mindful of the API usage limits for the external data providers you are using (Finnhub, CoinGecko, etc.). Implement caching and error handling to avoid exceeding these limits.
*   **Error Handling:**  The application includes basic error logging, but you should implement more robust error handling and monitoring for a production environment.
*   **Data Accuracy:** The accuracy of the simulated trading environment depends on the real-time data provided by the external APIs.  These APIs may have occasional outages or data inaccuracies.
*   **Scalability:**  For a production environment, consider using a more scalable database (e.g., PostgreSQL) and deploying the application using a platform like Google Cloud Run or Kubernetes.

## Contributing

Contributions are welcome!  Please submit pull requests with bug fixes, new features, or improvements to the documentation.

## License

[Choose a license and add it here.  For example, MIT License]
