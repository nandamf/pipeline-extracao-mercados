# 🛒 Retail Data Engineering Pipeline

A production-ready Data Engineering project that collects, processes, and analyzes supermarket product data using a modern Medallion Architecture (Bronze, Silver, Gold).

This project demonstrates the design and implementation of a scalable ETL pipeline capable of extracting data from multiple retailers, validating and standardizing product information, and generating analytics-ready datasets for Business Intelligence platforms.

---

## 🚀 Features

- Multi-source web scraping
- API integration (GraphQL & REST)
- Modular scraper architecture
- Automated ETL pipeline
- Bronze, Silver and Gold Data Lake layers
- Product normalization
- EAN validation
- Data quality scoring
- Duplicate detection and removal
- Partitioned Parquet storage
- Metadata and lineage tracking
- Production-ready logging
- Cloud-ready architecture

---

# 📊 Architecture

```text
                    Supermarket APIs / Websites
                               │
                               ▼
                        Web Scrapers
                               │
                               ▼
                     Bronze Layer (Raw Data)
                               │
                               ▼
              Silver Layer (Clean & Standardized)
                               │
                               ▼
                Gold Layer (Analytics & KPIs)
                               │
                               ▼
                    BigQuery (Next Phase)
                               │
                               ▼
                    Looker Studio Dashboard
                               ▲
                               │
                    Airflow Orchestration
```

---

# 🏗 Project Overview

The pipeline automatically extracts product information from multiple Brazilian supermarket retailers and processes it through a complete Data Lake architecture.

Currently supported retailers:

- ✅ Atacadão (GraphQL)
- ✅ Carrefour
- ✅ Mix Mateus (Algolia API)

The project was designed with scalability in mind, allowing new retailers to be added without changing the pipeline orchestration.

---

# 🥉 Bronze Layer

The Bronze layer stores immutable raw data exactly as received from each retailer.

### Responsibilities

- Raw data ingestion
- Audit trail preservation
- Metadata generation
- Schema preservation
- Partitioned Parquet storage

---

# 🥈 Silver Layer

The Silver layer transforms raw data into standardized datasets.

### Transformations

- Product name normalization
- Price normalization
- Unit standardization
- Brand cleaning
- Category mapping
- EAN checksum validation
- Duplicate removal
- Quality score calculation

---

# 🥇 Gold Layer

The Gold layer generates business-ready datasets optimized for analytics.

### Outputs

- Product catalog
- Price comparison
- Market KPIs
- Category analytics
- Historical price datasets

---

# ⚙️ Tech Stack

## Languages

- Python
- SQL

## Data Engineering

- Pandas
- PyArrow
- Parquet
- ETL
- Data Lake
- Medallion Architecture

## Web Scraping

- BeautifulSoup
- GraphQL
- REST APIs

## Data Storage

- SQLite
- Parquet

## Development

- Git
- Pytest
- Logging

---

# 📂 Project Structure

```text
extract_mercados/

├── scrapers/
├── common/
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── tests/
├── docs/
├── run_pipeline.py
└── README.md
```

---

# ▶ Pipeline Execution

```bash
python run_pipeline.py
```

Pipeline workflow:

```text
Generate EANs
      │
      ▼
Extraction
      │
      ▼
Bronze
      │
      ▼
Silver
      │
      ▼
Gold
```

---

# 📈 What This Project Demonstrates

This project showcases practical experience with modern Data Engineering concepts, including:

- ETL pipeline development
- Data Lake architecture
- Medallion Architecture
- Web Scraping
- API Integration
- Data Validation
- Data Quality Monitoring
- Metadata & Lineage
- Partitioned Data Storage
- Production Logging
- Modular Software Design
- Scalable Data Processing

---

# 📊 Current Status

## ✅ Completed

- Multi-market scraping
- Bronze layer
- Silver layer
- Gold layer
- Automated ETL pipeline
- Data normalization
- Data quality validation
- EAN verification
- Duplicate detection
- Metadata generation
- Partitioned Parquet storage
- Unit tests

## 🚧 Planned Improvements

- BigQuery integration
- Looker Studio dashboards
- Apache Airflow orchestration
- Docker support
- CI/CD pipeline

---

# 📚 Documentation

Additional technical documentation is available in the **docs/** directory.

- Bronze Architecture
- Silver Architecture
- Gold Architecture
- Operations Guide
- Quick Start Guide
- Implementation Roadmap

---

# 🎯 Project Goals

This project was developed to demonstrate real-world Data Engineering practices used in production environments.

It focuses on building scalable ETL pipelines capable of collecting data from multiple sources, ensuring data quality, and delivering analytics-ready datasets while following industry best practices.

---

# 🔮 Future Roadmap

- Cloud-native architecture with Google BigQuery
- Automated workflow orchestration using Apache Airflow
- Business dashboards with Looker Studio
- Dockerized deployment
- CI/CD with GitHub Actions
- Support for additional supermarket retailers

---

# 📄 License

This project was developed for educational and portfolio purposes.
