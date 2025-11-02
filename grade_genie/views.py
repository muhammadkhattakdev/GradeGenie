from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.shortcuts import render
import base64
from .grading_agent import ExamGradingAgent


@csrf_exempt
@require_http_methods(["POST"])
def grade_papers(request):
    """
    API endpoint to grade exam papers
    
    Expects:
        - images: List of base64 encoded images
        - instructions: Text with specific grading instructions
        
    Returns:
        - success: Boolean
        - graded_images: List of base64 encoded images with grades
        - grades: List of grade information
        - error: Error message if any
    """
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            images_base64 = data.get('images', [])
            instructions = data.get('instructions', '')
        else:
            # Handle multipart/form-data
            images_base64 = request.POST.getlist('images')
            instructions = request.POST.get('instructions', '')
            
            # Also check for file uploads
            uploaded_files = request.FILES.getlist('images')
            if uploaded_files:
                images_base64 = []
                for uploaded_file in uploaded_files:
                    image_bytes = uploaded_file.read()
                    images_base64.append(base64.b64encode(image_bytes).decode('utf-8'))
        
        # Validate input
        if not images_base64 or len(images_base64) == 0:
            return JsonResponse({
                'success': False,
                'error': 'No images provided'
            }, status=400)
        
        # Convert base64 images to bytes
        image_bytes_list = []
        for img_b64 in images_base64:
            # Remove data URL prefix if present
            if ',' in img_b64:
                img_b64 = img_b64.split(',')[1]
            image_bytes_list.append(base64.b64decode(img_b64))
        
        # Initialize grading agent
        agent = ExamGradingAgent()
        
        # Grade the papers
        result = agent.grade_papers(image_bytes_list, instructions)
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error occurred')
            }, status=500)
        
        # Convert graded images back to base64
        graded_images_base64 = []
        for img_bytes in result['graded_images']:
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            graded_images_base64.append(f"data:image/jpeg;base64,{img_b64}")
        
        return JsonResponse({
            'success': True,
            'graded_images': graded_images_base64,
            'grades': result['grades']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)
    

def home(request):

    return render(request, 'index.html')