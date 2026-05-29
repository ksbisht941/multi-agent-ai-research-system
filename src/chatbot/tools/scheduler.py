import os
import logging
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from chatbot.config import settings

logger = logging.getLogger(__name__)

# Use the configured output folder when available.
ROOT_DIR = Path(__file__).resolve().parents[3]
OUTPUT_DIR = settings.abs_output_path if settings else ROOT_DIR / "data" / "output"

@tool
def generate_day_plan(tasks: list[str], start_hour: int = 7) -> dict:
    """
    Generate a structured day plan from a list of user tasks.
    Each task is sequentially assigned a 1-hour time block.
    Use this tool when users ask to schedule or plan their day with specific activities.
    
    Args:
        tasks: A list of task descriptions to plan (e.g. ['Gym', 'Coding', 'Lunch']).
        start_hour: The starting hour of the schedule (24-hour format, defaults to 7).
        
    Returns:
        A dictionary containing the schedule's date and an array of time blocks with assigned tasks.
    """
    logger.info(f"Day plan tool invoked with {len(tasks)} tasks starting at {start_hour}:00")
    schedule = []
    current_hour = start_hour

    for task in tasks:
        start_time = f"{current_hour:02d}:00"
        end_time = f"{current_hour + 1:02d}:00"
        schedule.append({
            "start": start_time,
            "end": end_time,
            "task": task.strip()
        })
        current_hour += 1

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "schedule": schedule
    }

@tool
def generate_schedule_pdf(plan: dict, filename: str = "daily_plan.pdf") -> dict:
    """
    Generate a beautifully styled, print-ready PDF document for a structured day plan.
    Use this tool when the user wants to download, save, or export their generated schedule.
    
    Args:
        plan: The structured day plan dictionary returned by generate_day_plan.
              Must follow structure: {"date": "YYYY-MM-DD", "schedule": [{"start": "HH:MM", "end": "HH:MM", "task": "..."}]}
        filename: The desired name of the output PDF file (defaults to 'daily_plan.pdf').
        
    Returns:
        A dictionary indicating execution 'status' ('success' or 'error') and the downloadable 'file_path'.
    """
    logger.info(f"PDF generator tool invoked for filename: {filename}")
    try:
        # Guarantee output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Guard filename to prevent path traversal
        clean_filename = Path(filename).name
        if not clean_filename.endswith(".pdf"):
            clean_filename += ".pdf"
            
        full_path = OUTPUT_DIR / clean_filename
        
        # Build PDF
        pdf = SimpleDocTemplate(
            str(full_path),
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        
        # Custom elegant typography styles
        title_style = ParagraphStyle(
            "ScheduleTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#2E3A59"), # Premium slate blue
            alignment=1, # Centered
            spaceAfter=20
        )
        
        meta_style = ParagraphStyle(
            "ScheduleMeta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=colors.HexColor("#6B778C"),
            spaceAfter=15
        )
        
        heading_style = ParagraphStyle(
            "ScheduleHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#172B4D"),
            spaceBefore=15,
            spaceAfter=8
        )
        
        elements = []
        
        # Header title
        elements.append(Paragraph("DAILY PRODUCTIVITY SCHEDULE", title_style))
        elements.append(Spacer(1, 10))
        
        # Metadata information
        date_str = plan.get("date", datetime.now().strftime("%Y-%m-%d"))
        elements.append(Paragraph(f"<b>Planned Date:</b> {date_str}", meta_style))
        elements.append(Paragraph(f"<b>Generated On:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
        elements.append(Spacer(1, 10))
        
        # Table data initialization
        table_data = [["Start Time", "End Time", "Activity / Task"]]
        
        for item in plan.get("schedule", []):
            table_data.append([item["start"], item["end"], item["task"]])
            
        # Create Table (widths: Start 100, End 100, Task 300)
        table = Table(table_data, colWidths=[100, 100, 310])
        
        # Modern, premium table styling (harmonious colors, clean grid lines)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E3A59")), # Slate blue header
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            # Alternating row colors for high readability
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F5F7")),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#172B4D")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 8),
            # Outer boundary and inner grids
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DFE1E6")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#172B4D")),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 25))
        
        # Schedule Notes
        elements.append(Paragraph("Productivity Guidelines:", heading_style))
        bullet_style = styles["Bullet"]
        elements.append(Paragraph("Focus single-mindedly on the task during its assigned hourly slot.", bullet_style))
        elements.append(Paragraph("Take short 5-minute breaks between blocks to maintain peak energy.", bullet_style))
        elements.append(Paragraph("Celebrate small completion wins to sustain long-term execution momentum.", bullet_style))
        
        # Build Document
        pdf.build(elements)
        logger.info(f"PDF successfully built and saved to {full_path}")
        
        return {
            "status": "success",
            "file_path": clean_filename,
            "full_path": str(full_path)
        }
    except Exception as e:
        logger.error(f"Failed to generate schedule PDF: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to build PDF: {str(e)}"
        }
