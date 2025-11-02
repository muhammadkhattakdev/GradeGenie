"""
LangGraph-based Exam Grading Agent using Gemini (Official Google SDK)
File: grading_agent.py
"""
import os
import base64
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
import io


class GradingState(TypedDict):
    """State for the grading workflow"""
    images: List[bytes]  # List of image bytes
    instructions: str
    current_index: int
    grades: List[dict]  # List of {image_bytes, grade, feedback}
    error: str


class ExamGradingAgent:
    def __init__(self, api_key: str = None):
        """Initialize the grading agent with Gemini"""
        self.api_key = settings.GOOGLE_API_KEY
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(GradingState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("grade_paper", self._grade_paper)
        workflow.add_node("add_marks_to_image", self._add_marks_to_image)
        workflow.add_node("next_paper", self._next_paper)
        
        # Add edges
        workflow.set_entry_point("validate_input")
        workflow.add_edge("validate_input", "grade_paper")
        workflow.add_edge("grade_paper", "add_marks_to_image")
        workflow.add_edge("add_marks_to_image", "next_paper")
        
        # Conditional edge: continue or end
        workflow.add_conditional_edges(
            "next_paper",
            self._should_continue,
            {
                "continue": "grade_paper",
                "end": END
            }
        )
        
        return workflow.compile()
    
    def _validate_input(self, state: GradingState) -> GradingState:
        """Validate input data"""
        if not state.get("images") or len(state["images"]) == 0:
            state["error"] = "No images provided"
            return state
        
        if "current_index" not in state:
            state["current_index"] = 0
        
        if "grades" not in state:
            state["grades"] = []
        
        return state
    
    def _grade_paper(self, state: GradingState) -> GradingState:
        """Grade the current exam paper using Gemini Vision"""
        try:
            current_idx = state["current_index"]
            image_bytes = state["images"][current_idx]
            instructions = state.get("instructions", "")
            
            # Load image from bytes
            image = Image.open(io.BytesIO(image_bytes))
            
            # Create the grading prompt
            prompt = f"""You are an expert teacher grading exam papers. 
Analyze this exam paper image carefully and provide:
1. A numerical grade/score (e.g., 85/100, 92/100, or appropriate format)
2. Brief feedback on the student's performance

Additional Instructions from Teacher: {instructions if instructions else 'None'}

Be fair, constructive, and professional in your evaluation.

Provide your response in the following format:
GRADE: [score]
FEEDBACK: [your brief feedback]"""
            
            # Call Gemini with vision - pass content as a list
            response = self.model.generate_content(
                contents=[prompt, image],
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                )
            )
            result_text = response.text
            
            # Parse the response
            grade = "N/A"
            feedback = result_text
            
            if "GRADE:" in result_text:
                parts = result_text.split("FEEDBACK:")
                grade_part = parts[0].replace("GRADE:", "").strip()
                grade = grade_part
                if len(parts) > 1:
                    feedback = parts[1].strip()
            
            # Store the grading result
            state["grades"].append({
                "image_bytes": image_bytes,
                "grade": grade,
                "feedback": feedback
            })
            
        except Exception as e:
            state["error"] = f"Error grading paper {current_idx}: {str(e)}"
        
        return state
    
    def _add_marks_to_image(self, state: GradingState) -> GradingState:
        """Add grade marks to the exam paper image"""
        try:
            current_idx = state["current_index"]
            grade_info = state["grades"][current_idx]
            
            # Load image
            image = Image.open(io.BytesIO(grade_info["image_bytes"]))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create drawing context
            draw = ImageDraw.Draw(image)
            
            # Try to use a nice font, fall back to default if not available
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except:
                    font = ImageFont.load_default()
            
            # Prepare text
            grade_text = f"Grade: {grade_info['grade']}"
            
            # Calculate text position (top-center)
            bbox = draw.textbbox((0, 0), grade_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (image.width - text_width) // 2
            y = 20
            
            # Draw background rectangle for better visibility
            padding = 15
            draw.rectangle(
                [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
                fill='red',
                outline='darkred',
                width=3
            )
            
            # Draw grade text
            draw.text((x, y), grade_text, fill='white', font=font)
            
            # Convert back to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr.seek(0)
            
            # Update the image bytes with marked version
            state["grades"][current_idx]["image_bytes"] = img_byte_arr.getvalue()
            
        except Exception as e:
            state["error"] = f"Error adding marks to image {current_idx}: {str(e)}"
        
        return state
    
    def _next_paper(self, state: GradingState) -> GradingState:
        """Move to the next paper"""
        state["current_index"] += 1
        return state
    
    def _should_continue(self, state: GradingState) -> str:
        """Determine if we should continue grading or end"""
        if state.get("error"):
            return "end"
        
        if state["current_index"] >= len(state["images"]):
            return "end"
        
        return "continue"
    
    def grade_papers(self, images: List[bytes], instructions: str = "") -> dict:
        """
        Grade multiple exam papers
        
        Args:
            images: List of image bytes
            instructions: Specific grading instructions from teacher
            
        Returns:
            dict with 'success', 'graded_images' (list of bytes), and optional 'error'
        """
        initial_state = {
            "images": images,
            "instructions": instructions,
            "current_index": 0,
            "grades": [],
            "error": None
        }
        
        # Run the workflow
        final_state = self.workflow.invoke(initial_state)
        
        if final_state.get("error"):
            return {
                "success": False,
                "error": final_state["error"]
            }
        
        # Extract graded images
        graded_images = [grade["image_bytes"] for grade in final_state["grades"]]
        
        return {
            "success": True,
            "graded_images": graded_images,
            "grades": [{"grade": g["grade"], "feedback": g["feedback"]} for g in final_state["grades"]]
        }