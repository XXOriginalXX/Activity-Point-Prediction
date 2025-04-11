# 🎓 AURA Activity Points Predictor

This is a Flask-based microservice designed for the AURA platform. It extracts text from uploaded certificates (PDFs or images), identifies the certificate type, and assigns activity points based on predefined rules. It supports OCR and PDF parsing and is hosted on **Render.io**.

---

## 🚀 Features

- 🔍 Intelligent text extraction using **Tesseract OCR**
- 🧾 PDF-to-image conversion with **pdf2image**
- 🧠 Smart classification of certificate types
- 📊 Points allocation based on activity (NPTEL, Internship, Hackathon, etc.)
- 📡 REST API endpoint for seamless integration
- 🌐 CORS enabled for cross-origin requests

---

## 📂 Supported File Types

- `.pdf`
- `.png`
- `.jpg`
- `.jpeg`

---

## 📦 Tech Stack

- **Flask** – Web framework
- **pytesseract** – OCR engine
- **pdf2image** – PDF to image converter
- **OpenCV** – Image preprocessing
- **PIL (Pillow)** – Image handling
- **NumPy** – Array processing
- **Render.io** – Hosting

---

