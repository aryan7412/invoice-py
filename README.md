````markdown
# Collection Radar 🔎

### A local AI assistant for prioritizing wholesale invoice collections

Collection Radar helps small wholesale businesses answer a simple question:

> **"Who should I follow up with first?"**

It takes an existing Excel/CSV invoice spreadsheet, learns from historical payment behaviour using **TabPFN**, and ranks current invoices by **late-payment risk** and **potential cash exposure**.

The goal is simple:

> Turn an existing spreadsheet into a practical collection priority list.

---

## 💡 Why I Built This

I built Collection Radar for my father, who runs a wholesale business.

He already had years of invoice and payment information in Excel, but deciding which customers to follow up with often meant manually going through invoices and remembering previous payment behaviour.

The problem wasn't a lack of data.

**It was turning that data into a decision.**

So I built a small local AI assistant that answers:

> **"Which invoices should I look at first?"**

---

## ✨ Features

- 📊 Upload an existing Excel or CSV file
- 🤖 Use **TabPFN** for tabular machine learning
- 🔒 Run predictions locally
- 📴 Designed to work without internet during inference after setup
- 🔴 High / 🟠 Medium / 🟢 Low risk classification
- 💰 Calculate potential cash exposure
- 📋 Rank invoices by collection priority
- 📥 Export results as CSV
- 🧾 Works with existing spreadsheet workflows
- 🖥️ Simple Streamlit interface

---

## 🧠 How It Works

The application learns from historical invoices where the payment outcome is known.

Example data:

```text
Customer
Invoice Amount
Average Payment Days
Previous Late Payments
Credit Period
Outstanding Amount
Region
Paid Late
````

The **`Paid Late`** column provides the historical outcome that the model learns from.

Collection Radar then estimates the late-payment risk of current invoices.

### Potential Cash Exposure

The application also considers the potential financial impact:

```text
Potential Exposure
= Late Payment Probability × Invoice Amount
```

This helps answer not only:

> "Which invoice is risky?"

but also:

> **"Which risky invoice could have the biggest impact?"**

---

## 🔄 Workflow

```text
Excel / CSV
     │
     ▼
Upload Spreadsheet
     │
     ▼
Map Columns
     │
     ▼
Historical Payment Data
     │
     ▼
Local TabPFN Model
     │
     ▼
Late-Payment Risk
     │
     ▼
Potential Cash Exposure
     │
     ▼
Collection Priority
```

---

# 🚀 How to Run

## 1. Clone the Repository

```bash
git clone https://github.com/aryan7412/invoice-py.git
cd invoice-py
```

---

## 2. Create the Environment

### macOS / Linux

This project is recommended with **Python 3.12**.

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
```

Check your Python version:

```bash
python --version
```

You should see:

```text
Python 3.12.x
```

### Windows

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 4. Start Collection Radar

```bash
python -m streamlit run app.py
```

Then open:

**[http://localhost:8501](http://localhost:8501)**

Streamlit should open the application automatically in your browser.

---

## 🤖 First-Time TabPFN Setup

On the first run, TabPFN may need to complete its initial setup and download the required model files.

An internet connection is required for this initial setup.

Once the model has been downloaded and cached locally, inference can be performed locally.

The first setup may take some time because the model files are relatively large.

---

## 📴 Offline Inference

After the initial TabPFN setup is complete:

```text
Internet ON
     │
     ▼
Initial Model Setup
     │
     ▼
Model Cached Locally
     │
     ▼
Internet OFF
     │
     ▼
Upload Excel
     │
     ▼
Run Collection Radar
```

The prediction itself runs locally on the machine.

---

## 📄 Spreadsheet Data

Collection Radar works with spreadsheet-based invoice data.

Useful columns include:

```text
Customer
Invoice ID
Invoice Amount
Average Payment Days
Previous Late Payments
Credit Period Days
Outstanding Amount
Region
Paid Late
```

The application allows you to map your spreadsheet columns to the required fields.

### Historical Data

Historical invoices should contain a known payment outcome:

```text
Paid Late = Yes / No
```

This gives the model examples from which it can learn.

### Current Invoices

Current outstanding invoices are then scored based on patterns learned from historical data.

---

## 🧪 Demo Data

The repository includes synthetic wholesale invoice data that can be used to test the application.

The demo data is **not real customer data**.

It is provided so you can run Collection Radar without needing a real business spreadsheet.

---

## 🔐 Privacy First

Collection Radar is designed around **local-first usage**.

Your invoice data does not need to be uploaded to a cloud AI service for prediction.

For real business data:

* Keep the spreadsheet on the local machine.
* Do not commit private invoices to GitHub.
* Do not put customer information into the public repository.
* Use synthetic data when sharing the project publicly.

---

## 📁 Project Structure

```text
invoice-py/
│
├── app.py
├── engine.py
├── demo_data.py
├── demo_wholesale_data.xlsx
├── requirements.txt
├── README.md
├── .gitignore
├── run.sh
│
├── data/
│   └── .gitkeep
│
└── .streamlit/
    └── config.toml
```

| File                       | Purpose                                           |
| -------------------------- | ------------------------------------------------- |
| `app.py`                   | Streamlit user interface                          |
| `engine.py`                | Data preparation and ML logic                     |
| `demo_data.py`             | Generates synthetic demo data                     |
| `demo_wholesale_data.xlsx` | Example spreadsheet                               |
| `requirements.txt`         | Python dependencies                               |
| `run.sh`                   | Optional startup script                           |
| `.gitignore`               | Prevents private/local files from being committed |

---

## ⚠️ Important

Collection Radar provides **risk estimates**, not guarantees.

A high-risk prediction does not mean that a customer definitely will not pay.

The quality of predictions depends on the quality and quantity of historical data available.

Use the results as a **decision-support tool**, not as a replacement for business judgement.

---

# 🛣️ Roadmap

## V1 — Current

* [x] Excel/CSV upload
* [x] Column mapping
* [x] Local TabPFN inference
* [x] Risk classification
* [x] Potential cash exposure
* [x] Collection priority ranking
* [x] CSV export

## V2 — Planned

### TabPFN vs XGBoost

The next version will benchmark **TabPFN against XGBoost** using the same historical dataset.

Planned metrics:

* ROC-AUC
* F1 Score
* Accuracy
* Runtime

The goal is to measure which model actually performs better rather than assuming one is superior.

### Future Features

* Due dates
* Days overdue
* Aging buckets
* Outstanding balance
* Customer-level risk
* Customer payment history
* Collection/follow-up status
* Risk contributing signals
* Cash-flow forecasting

---

# ❤️ Built for a Friend

This project was built for my father as part of the **Hacktoberfest Weekend Challenge — Build for a Friend**.

I had already seen the problem in his day-to-day work.

He had the data.

He had the experience.

What was missing was a simple way to turn all that information into a priority list.

So I built Collection Radar to answer one question:

> **"Who should I call first?"**

Built with open source, local AI, and a lot of love. ❤️

---

## 🔗 Links

**GitHub:**
[https://github.com/aryan7412/invoice-py](https://github.com/aryan7412/invoice-py)

---

## 👨‍💻 Author

**Aryan Samal**

Built for my dad. Built with open source. Built locally.

```
```
