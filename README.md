# Backend Overview: LBP-USD Exchange App

## Introduction
The **LBP-USD Exchange App** serves as the backend for a multi-platform application designed to support a web frontend, an Android mobile app built with Kotlin, and a desktop application using JavaFX. The API allows users to register, authenticate, and conduct transactions involving USD to LBP and LBP to USD exchanges. It computes average exchange rates based on recent historical data, giving users a transparent view of currency trends.

The API also offers additional features such as wallet management, dealer management, multi-factor authentication (MFA), accessibility options, and news summarization.

All API endpoints are documented in OpenAPI format which can be inspected by loading `openapi.yaml` in an appropriate renderer (e.g. Swagger).

## Key Features

- **User Management**
  - Register new users and authenticate them using JWT tokens.
  - Retrieve user details and enable multi-factor authentication (MFA) via TOTP.
  - Reset user passwords and verify email addresses.

- **Currency & Exchange Transactions**
  - Submit exchange transactions between USD and LBP (and vice versa).
  - Track transaction volumes and compute average exchange rates over various time periods (daily, monthly, yearly).
  
- **Wallet Management**
  - Retrieve wallet details, including balances in USD and LBP.
  - Add, retrieve, and delete wallet transactions.
  - Reset wallet balances and manage wallet status.

- **Exchange Rate Data**
  - Fetch daily, hourly, and monthly exchange rates.
  - Calculate trends and volatility based on historical data.
  - Sonification of exchange rate and transaction volumes for accessibility purposes.

- **Exchange Offers**
  - Create, update, and delete peer-to-peer exchange offers.
  - Mark offers as accepted and track available and taken offers.
  
- **Dealer Management**
  - Register, update, and delete exchange dealers.
  - View dealer information, including exchange rates and ratings.

- **News Management**
  - Retrieve and summarize news articles that may impact currency exchange rates.
  - Provide AI-generated summaries with natural language and audio text-to-speech output.

- **Accessibility Features**
  - Allow users to enable features like sonification (audio feedback for exchange rate changes) and narration for exchange rate and wallet summaries.
  - Implement accessibility for users who require visual or auditory assistance with the app.
  - Save and load accessibility settings for syncing across multiple platforms.

## Live Online Deployment

> **Backend Note!**  
> The Render free instance will spin down with inactivity, which can delay initial requests by 50 seconds or more.\
> If the backend is not responsive, try rerequesting in case of timeout until the Render instance goes live again.

> **Database Note!**  
> The Database size is limited to 5 gigabytes only. The database might also be slow for accesses for many users due to limited bandwidth in the free tier.


The CI/CD live deployment version of this backend can be located at the following link: https://exchange-openapi-group-14.onrender.com/. The backend is hosted by [Render](https://render.com/) and the MySQL database is hosted by [Aiven](https://aiven.io/) using the free tier for both.

Due to latencies and network delays, the backend will feel slower than a local deployment.

## Local Deployment

### Installing MySQL

For a local deployment, you must have MySQL set up on your system. This can be done by following [this link](https://www.mysql.com/).

Once MySQL is installed, create a database to house the backend tables. This can be done by executing the following in a MySQL Shell. You can name the database anything you like but `exchange` is recommended.
```sql
CREATE SCHEMA exchange;
```

Please note of your MySQL username (usually `root`), password, host (usually `localhost`), port (usually `3306`), and chosen database name (`exchange` is recommended above).

### Obtaining the Keys

* This app requires a mail account to send verification and password reset emails.
You can use Gmail if you like, make sure to generate an app password to be able to authenticate it with the Flask mail app. You can read more about this [here](https://support.google.com/mail/answer/185833?hl=en).

    If you use another mail service, you need to obtain mail server information from your provider.

* You require a key from MarketAux for obtaining world news. This can be obtained free from [here](https://www.marketaux.com/register) by registering at MarketAux.

* You need a Google Gemini key for accessibility and news features of this app. A free tier key can be obtained from [here](https://aistudio.google.com/apikey) which only requires a Google account.

* *(Optional, but recommended)* For enhanced text-to-speech services for the narrated summaries feature of this app, we support AWS Polly over Google TTS which requires AWS keys. You can sign up for their free tier [here](https://aws.amazon.com/free/) which requires credit card information. After that, obtain an IAS Access Key, Secret Key, and Session Token.

### Running The Backend

To run the backend, you must clone this repo \[https://github.com/EECE430LSpring2025/exchange-openapi-group-14\] and navigate to the `backend` folder.

You must also create an `.env` file storing your own secrets for the backend based on the keys and MySQL database information you obtained above. Begin by generating secure SECRET_KEY and SECURITY_PASSWORD_SALT values (entropy of 150 or greater bits is recommended). Note that SECRET_KEY must be encoded as a binary (byte) value.

Then, you can create `.env` with the following content, replacing content within angle brackets with their respective values. You must also set MAIL_SERVER, MAIL_PORT, and MAIL_USE_TLS as appropriate if you do not wish to use Gmail.
```
DB_USER=<DB USERAME>
DB_PASSWORD=<DB PASSWORD>
DB_HOST=<DB HOST>
DB_PORT=<DB PORT>
DB_NAME=<DB NAME>
SECRET_KEY=<SECRET_KEY>
SECURITY_PASSWORD_SALT=<SECURITY_PASSWORD_SALT>
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=<Gmail Mail>
MAIL_PASSWORD=<Gmail App Password>

MARKETAUX_KEY=<MarketAux API Key>
GEMINI_KEY=<Gemini API Key>

AWS_ACCESS_KEY=<Optional AWS Access Key, Leave Blank if None>
AWS_SECRET_KEY=<Optional AWS Secret Key, Leave Blank if None>
AWS_SESSION_TOKEN=<Optional AWS Session Token, Leave Blank if None>
```

> **Database Note!**  
> If the default database configuration is not satisfactory, feel free to create a `db.config.py` file with a `DB_CONFIG` variable which would hold your custom database information.


Using Python 3.13 or greater is highly recommended for optimal compatibility with the backend.

1. First of all, ensure you have python installed and on your path. You can verify by running the following command:
    ```bash
    python --version
    ```
    If this command fails, or a version less than 3.13 is reported, you can install the latest version from [the python website](https://www.python.org/).

2. Activate a virtual environment to easily manage the requirements of this project.
    ```bash
    python -m venv .venv
    ```
    
    This will create a virtual environment based on the system Python version.

3. Activate the virtual environment.
    ```bash
    myenv\Scripts\activate
    ```
    
    Your terminal should now have a `(.venv)` prompt preceeding the folder name.

4. Install all dependencies
    ```bash
    pip install --upgrade pip && pip install -r requirements.txt
    ```

5. Run data generator to fill with sample values (optional, but recommended if you are testing so that you get meaningful information).
    ```bash
    python util/datagen.py
    ```
    This script creates 5000 users and populates the database with sample transactions over the past two years at random time with random values such that the exchange rate varies between 80000 and 100000 for both USD-LBP and LBP-USD. Running it might take a few minutes depending on your processor speed.

6. Run the backend. This can be done with the below command
    ```bash
    python -m run
    ```
    The initial run might be delayed to bootstrap databases and load news information for the first time, then this task would happen asynchronously every 15 minutes on the backend and does not occur on first launch for subsequent runs of the backend.

### Running with Docker
The backend can also be served with a Docker instance with proper configuration. A sample `Dockerfile` is included with the repository.

