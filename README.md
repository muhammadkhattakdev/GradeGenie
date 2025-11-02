# Exam Grading AI Setup Guide

## Requirements

```txt
Django>=4.2.0
langgraph>=0.0.20
google-generativeai>=0.8.0
Pillow>=10.0.0
```

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up Google API Key:**
```bash
export GOOGLE_API_KEY='your-gemini-api-key-here'
```

Or add it to your Django settings.py:
```python
import os
os.environ['GOOGLE_API_KEY'] = 'your-api-key-here'
```

## Django Setup

1. **Add the view to your urls.py:**
```python
from django.urls import path
from . import views

urlpatterns = [
    path('api/grade/', views.grade_papers, name='grade_papers'),
]
```

2. **Project Structure:**
```
your_project/
├── grading_agent.py      # The LangGraph agent
├── views.py              # Django view with API endpoint
├── urls.py               # URL configuration
└── requirements.txt
```

## API Usage

**Endpoint:** `POST /api/grade/`

**Request Format (JSON):**
```json
{
  "images": [
    "base64_encoded_image_1",
    "base64_encoded_image_2"
  ],
  "instructions": "Focus on grammar and content quality. Maximum score is 100."
}
```

**Request Format (multipart/form-data):**
```
images: [file1, file2, ...]
instructions: "Your grading instructions here"
```

**Response Format:**
```json
{
  "success": true,
  "graded_images": [
    "data:image/jpeg;base64,graded_image_1",
    "data:image/jpeg;base64,graded_image_2"
  ],
  "grades": [
    {
      "grade": "85/100",
      "feedback": "Good understanding of concepts..."
    }
  ]
}
```

## How It Works

1. **Teacher uploads images** and provides instructions through your frontend
2. **Django view receives** the data at `/api/grade/`
3. **LangGraph workflow** processes each paper:
   - Validates input
   - Uses Gemini Vision to analyze and grade each paper
   - Adds grade overlay to the image
   - Moves to next paper
4. **Returns graded images** with marks overlaid on top

## Features

- ✅ Multi-image batch processing
- ✅ Custom grading instructions support
- ✅ Visual grade overlay on images
- ✅ Detailed feedback for each paper
- ✅ Error handling and validation
- ✅ LangGraph workflow for robust processing

## Notes

- Ensure your Google Cloud project has Gemini API enabled
- Images are processed sequentially for reliability
- The agent uses `gemini-1.5-flash` for fast, cost-effective grading
- Grades are displayed in a red badge at the top-center of each image
