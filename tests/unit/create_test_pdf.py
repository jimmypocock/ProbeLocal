#!/usr/bin/env python3
"""Create a sample PDF for testing ProbeLocal"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

def create_test_pdf():
    """Create a sample invoice PDF for testing"""
    
    filename = "test_invoice.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Add content
    y_position = height - inch
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(inch, y_position, "INVOICE")
    y_position -= 40
    
    # Invoice details
    c.setFont("Helvetica", 12)
    c.drawString(inch, y_position, "Invoice #: INV-2025-001")
    y_position -= 20
    c.drawString(inch, y_position, "Date: June 27, 2025")
    y_position -= 40
    
    # Customer info
    c.setFont("Helvetica-Bold", 14)
    c.drawString(inch, y_position, "Bill To:")
    y_position -= 20
    c.setFont("Helvetica", 12)
    c.drawString(inch, y_position, "Acme Corporation")
    y_position -= 15
    c.drawString(inch, y_position, "123 Business Street")
    y_position -= 15
    c.drawString(inch, y_position, "San Francisco, CA 94105")
    y_position -= 40
    
    # Items header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(inch, y_position, "Description")
    c.drawString(4*inch, y_position, "Quantity")
    c.drawString(5*inch, y_position, "Price")
    c.drawString(6*inch, y_position, "Total")
    y_position -= 20
    
    # Line
    c.line(inch, y_position, 7*inch, y_position)
    y_position -= 20
    
    # Items
    c.setFont("Helvetica", 12)
    items = [
        ("AI Consulting Services", "10 hours", "$150.00", "$1,500.00"),
        ("Model Training", "1 project", "$2,500.00", "$2,500.00"),
        ("Data Processing", "5 hours", "$100.00", "$500.00"),
        ("Technical Support", "8 hours", "$125.00", "$1,000.00")
    ]
    
    for item in items:
        c.drawString(inch, y_position, item[0])
        c.drawString(4*inch, y_position, item[1])
        c.drawString(5*inch, y_position, item[2])
        c.drawString(6*inch, y_position, item[3])
        y_position -= 20
    
    # Totals
    y_position -= 20
    c.line(5.5*inch, y_position, 7*inch, y_position)
    y_position -= 20
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5*inch, y_position, "Subtotal:")
    c.drawString(6*inch, y_position, "$5,500.00")
    y_position -= 20
    
    c.drawString(5*inch, y_position, "Tax (8.5%):")
    c.drawString(6*inch, y_position, "$467.50")
    y_position -= 20
    
    c.drawString(5*inch, y_position, "Total Due:")
    c.drawString(6*inch, y_position, "$5,967.50")
    
    # Payment terms
    y_position -= 60
    c.setFont("Helvetica", 10)
    c.drawString(inch, y_position, "Payment Terms: Net 30 days")
    y_position -= 15
    c.drawString(inch, y_position, "Please make checks payable to: AI Solutions Inc.")
    
    # Footer
    y_position = inch
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(inch, y_position, "Thank you for your business!")
    
    # Save the PDF
    c.save()
    
    print(f"✅ Created test PDF: {filename}")
    print(f"📍 Location: {os.path.abspath(filename)}")
    print("\n📝 Test Questions to Ask:")
    print("- What is the invoice number?")
    print("- What is the total amount due?")
    print("- Who is the customer?")
    print("- What services were provided?")
    print("- What is the tax rate?")
    print("- When is payment due?")

if __name__ == "__main__":
    try:
        create_test_pdf()
    except ImportError:
        print("❌ reportlab not installed. Installing...")
        import subprocess
        subprocess.check_call(["pip", "install", "reportlab"])
        print("✅ Installed reportlab. Running again...")
        create_test_pdf()