#!/usr/bin/env python3
"""Create a simple test text file that can be used to test the system"""

def create_test_content():
    """Create a test document with structured content"""
    
    content = """ACME CORPORATION
INVOICE

Invoice Number: INV-2025-001
Date: June 27, 2025

BILL TO:
Tech Startup Inc.
456 Innovation Drive
San Francisco, CA 94105
Contact: John Doe
Email: john@techstartup.com

INVOICE DETAILS:

Item Description                    Quantity    Unit Price    Total
-------------------------------------------------------------------
AI Model Development                1 project   $15,000.00    $15,000.00
Data Processing Pipeline            40 hours    $150.00       $6,000.00
Machine Learning Consultation       20 hours    $200.00       $4,000.00
Custom API Integration              1 system    $3,500.00     $3,500.00
Technical Documentation             1 package   $1,500.00     $1,500.00

-------------------------------------------------------------------
                                              Subtotal:     $30,000.00
                                              Tax (8.5%):    $2,550.00
                                              TOTAL DUE:    $32,550.00

PAYMENT TERMS:
- Payment due within 30 days
- 2% discount if paid within 10 days
- Make checks payable to: ACME Corporation
- Wire transfer details available upon request

PROJECT SUMMARY:
This invoice covers the development of a custom AI solution including:
- Natural language processing model for customer service automation
- Real-time data processing pipeline handling 1M+ requests/day
- RESTful API with 99.9% uptime SLA
- Comprehensive documentation and training materials
- 90-day warranty and support period

ADDITIONAL NOTES:
- All intellectual property rights transferred upon full payment
- Source code will be delivered via secure GitHub repository
- Training session scheduled for July 15, 2025
- Monthly maintenance agreement available for $2,000/month

Thank you for your business!

For questions about this invoice, please contact:
Billing Department
ACME Corporation
billing@acmecorp.com
(555) 123-4567
"""
    
    # Save as text file
    with open("test_invoice.txt", "w") as f:
        f.write(content)
    
    print("✅ Created test_invoice.txt")
    print("\n📝 Sample Questions to Test:")
    print("1. What is the invoice number?")
    print("2. What is the total amount due?")
    print("3. Who is being billed?")
    print("4. What services were provided?")
    print("5. What is the tax amount?")
    print("6. When is the training session scheduled?")
    print("7. What is the payment deadline?")
    print("8. What discount is offered for early payment?")
    print("\n⚠️  Note: ProbeLocal expects PDF files. You'll need to:")
    print("1. Convert this to PDF, or")
    print("2. Use any existing PDF file you have")

if __name__ == "__main__":
    create_test_content()