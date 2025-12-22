# 🎓 SkillBuddy AI
 
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**SkillBuddy AI** is an AI-powered education management platform that merges academic efficiency with emotional intelligence. Designed for Admins, Teachers, and Students, it streamlines campus management, boosts engagement, and supports students’ mental well-being.

---

## 💡 Problem

Current educational platforms are fragmented:
- Admins juggle multiple systems
- Teachers lack tools to engage and evaluate efficiently
- Students suffer from academic burnout with little emotional support

---

## ✅ Solution

**SkillBuddy AI** solves this with a unified, intelligent system:
- Combines academic management and emotional analysis
- Delivers role-based dashboards and personalized insights
- Includes an AI chatbot and emotion recognition for better support

---

## 🔑 Key Features

- 🎓 **Role-based Dashboards**: Specialized interfaces for Admin, Teacher, and Student.
- 🤖 **AI Chatbot**: Real-time academic query resolution and motivational support via Gemini AI.
- 📸 **Emotion Analytics**: Facial expression analysis during login to monitor well-being.
- 🧠 **Stakeholder Feedback**: 
    - **Teachers**: High-stress alerts and emotional trend dashboards.
    - **Parents**: Simple, child-safe emotional summaries and early-warning alerts.
- 📈 **GPA & Academic Tracking**: Automated performance analytics and grade management.
- 📂 **LMS Core**: Course management, file/video uploads, and quiz engine.

---

## 🛠️ Tech Stack

| Layer       | Tools/Frameworks                           |
|-------------|---------------------------------------------|
| **Core**    | Django (Python), Django REST Framework      |
| **Frontend**| Vanilla JS, Bootstrap 5, FontAwesome, Chart.js|
| **AI/ML**   | MediaPipe, OpenCV, TensorFlow, Gemini API   |
| **Database**| SQLite (Development) / MySQL                |

---

## 🚀 Quick Run

To run the project on your local machine using the pre-configured virtual environment:

```bash
# 1. Access the project directory
cd SkillBuddy

# 2. Run the development server
./venv/bin/python manage.py runserver
```
Access the platform at: `http://127.0.0.1:8000/`

---

## 📸 Emotion Detection Flow

1. **Student Login**: Student inputs credentials and grants optional webcam consent.
2. **AI Analysis**: System captures facial data and processes it using **MediaPipe**.
3. **Data Recording**: Emotion (Happy, Neutral, Stressed, etc.) is recorded securely.
4. **Alert Trigger**: If negative trends (e.g., 3 days of stress) are detected, alerts are sent to teachers and parents.

---

## 👤 Author

**Shani Chauhan**  

