"""
PDF Generator Module
Handles generation of PDF files with lyrics (original and/or translated).
"""

import os
from datetime import datetime
from typing import Optional

# Optional import for reportlab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️  Warning: reportlab not installed. PDF generation feature will not work.")


class PDFGenerator:
    """Handles PDF generation for lyrics."""
    
    def __init__(self):
        """Initialize the PDF Generator."""
        pass
    
    def generate(self, lyrics: str, output_path: str, title: str = "Song Lyrics", 
                is_translation: bool = False, original_language: str = "Original",
                target_language: str = "Translated") -> bool:
        """
        Generate a PDF file with lyrics.
        
        Args:
            lyrics: Lyrics text to include in PDF
            output_path: Path where PDF will be saved
            title: Title for the PDF
            is_translation: Whether this is a translation
            original_language: Original language name
            target_language: Target language name (if translation)
            
        Returns:
            True if successful, False otherwise
        """
        if not REPORTLAB_AVAILABLE:
            print("✗ ReportLab not available. Please install: pip install reportlab")
            return False
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=letter,
                                  rightMargin=72, leftMargin=72,
                                  topMargin=72, bottomMargin=18)
            
            # Container for the 'Flowable' objects
            story = []
            
            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor='#1a1a1a',
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                textColor='#666666',
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Oblique'
            )
            
            lyrics_style = ParagraphStyle(
                'CustomLyrics',
                parent=styles['Normal'],
                fontSize=11,
                leading=16,
                textColor='#000000',
                spaceAfter=12,
                alignment=TA_LEFT,
                fontName='Helvetica'
            )
            
            # Add title
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # Add subtitle with language info
            if is_translation:
                subtitle_text = f"{target_language} Translation (Original: {original_language})"
            else:
                subtitle_text = f"Language: {original_language}"
            
            story.append(Paragraph(subtitle_text, subtitle_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Add date
            date_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
            story.append(Paragraph(date_text, subtitle_style))
            story.append(Spacer(1, 0.4*inch))
            
            # Add lyrics (split by lines and paragraphs)
            lyrics_lines = lyrics.split('\n')
            for line in lyrics_lines:
                if line.strip():
                    # Replace special characters for PDF
                    line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(line, lyrics_style))
                else:
                    story.append(Spacer(1, 0.1*inch))
            
            # Build PDF
            doc.build(story)
            print(f"✓ PDF generated successfully: {output_path}")
            return True
            
        except Exception as e:
            print(f"✗ PDF generation error: {e}")
            return False
    
    def generate_combined(self, original_lyrics: str, translated_lyrics: str, 
                         output_path: str, title: str = "Song Lyrics",
                         original_language: str = "Original",
                         target_language: str = "Translated") -> bool:
        """
        Generate a PDF with both original and translated lyrics.
        
        Args:
            original_lyrics: Original lyrics text
            translated_lyrics: Translated lyrics text
            output_path: Path where PDF will be saved
            title: Title for the PDF
            original_language: Original language name
            target_language: Target language name
            
        Returns:
            True if successful, False otherwise
        """
        combined_lyrics = f"ORIGINAL LYRICS ({original_language})\n{'='*60}\n\n{original_lyrics}\n\n\n{'='*60}\n\nTRANSLATION ({target_language})\n{'='*60}\n\n{translated_lyrics}"
        
        return self.generate(
            lyrics=combined_lyrics,
            output_path=output_path,
            title=f"{title} - Original & Translation",
            is_translation=True,
            original_language=original_language,
            target_language=target_language
        )

