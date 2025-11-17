#!/usr/bin/env python3
"""
Test script for Excel spreadsheet processing
"""

import sys
import os
sys.path.append('/home/azureuser/ai_platform/backend')

from app.utils.file_utils import extract_text_from_spreadsheet, detect_file_type

def test_excel_processing(excel_path):
    """Test Excel processing"""
    print(f"Testing Excel processing for: {excel_path}")
    
    # Check if file exists
    if not os.path.exists(excel_path):
        print(f"❌ File not found: {excel_path}")
        return
    
    # Detect file type
    try:
        file_type = detect_file_type(excel_path)
        print(f"✓ Detected file type: {file_type}")
    except Exception as e:
        print(f"❌ File type detection failed: {e}")
        return
    
    # Extract text from spreadsheet
    try:
        # Make a copy since the function deletes the file
        import shutil
        temp_path = f"/tmp/test_excel_{os.path.basename(excel_path)}"
        shutil.copy2(excel_path, temp_path)
        
        text_chunks = extract_text_from_spreadsheet(temp_path)
        print(f"✓ Text extraction successful!")
        print(f"✓ Number of chunks: {len(text_chunks)}")
        
        for i, chunk in enumerate(text_chunks, 1):
            print(f"\n--- Chunk {i} ---")
            print(chunk[:400] + "..." if len(chunk) > 400 else chunk)
            
    except Exception as e:
        print(f"❌ Text extraction failed: {e}")

def create_sample_excel():
    """Create a sample Excel file for testing"""
    try:
        import openpyxl
        from openpyxl import Workbook
        
        wb = Workbook()
        
        # Sheet 1 - Student Data
        ws1 = wb.active
        ws1.title = "Students"
        
        # Headers
        ws1['A1'] = 'Student ID'
        ws1['B1'] = 'Name'
        ws1['C1'] = 'Course'
        ws1['D1'] = 'Grade'
        ws1['E1'] = 'Status'
        
        # Sample data
        students = [
            [1001, 'Alice Johnson', 'Computer Science', 'A', 'Active'],
            [1002, 'Bob Smith', 'Mathematics', 'B+', 'Active'],
            [1003, 'Carol White', 'Physics', 'A-', 'Active'],
            [1004, 'David Brown', 'Chemistry', 'B', 'Inactive'],
            [1005, 'Eve Davis', 'Biology', 'A+', 'Active']
        ]
        
        for i, student in enumerate(students, 2):
            for j, value in enumerate(student, 1):
                ws1.cell(row=i, column=j, value=value)
        
        # Sheet 2 - Course Information
        ws2 = wb.create_sheet("Courses")
        ws2['A1'] = 'Course Code'
        ws2['B1'] = 'Course Name'
        ws2['C1'] = 'Credits'
        ws2['D1'] = 'Instructor'
        
        courses = [
            ['CS101', 'Introduction to Programming', 3, 'Dr. Smith'],
            ['MATH201', 'Calculus II', 4, 'Prof. Johnson'],
            ['PHYS101', 'General Physics', 4, 'Dr. Wilson'],
            ['CHEM101', 'General Chemistry', 3, 'Prof. Brown'],
            ['BIO101', 'Introduction to Biology', 3, 'Dr. Davis']
        ]
        
        for i, course in enumerate(courses, 2):
            for j, value in enumerate(course, 1):
                ws2.cell(row=i, column=j, value=value)
        
        # Sheet 3 - Statistics
        ws3 = wb.create_sheet("Statistics")
        ws3['A1'] = 'Metric'
        ws3['B1'] = 'Value'
        
        stats = [
            ['Total Students', 5],
            ['Active Students', 4],
            ['Average Grade', 'B+'],
            ['Completion Rate', '80%'],
            ['Total Courses', 5]
        ]
        
        for i, stat in enumerate(stats, 2):
            for j, value in enumerate(stat, 1):
                ws3.cell(row=i, column=j, value=value)
        
        sample_path = "/tmp/sample_spreadsheet.xlsx"
        wb.save(sample_path)
        print(f"✓ Created sample Excel file: {sample_path}")
        return sample_path
        
    except Exception as e:
        print(f"❌ Failed to create sample Excel file: {e}")
        return None

if __name__ == "__main__":
    print("=== Excel Processing Test ===")
    
    # Create a sample file
    sample_file = create_sample_excel()
    
    # Test with sample file
    if sample_file:
        test_excel_processing(sample_file)
    
    # You can also test with your own files
    test_files = [
        "/path/to/your/test/spreadsheet.xlsx",
        "/path/to/your/test/workbook.xls"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            test_excel_processing(test_file)
        else:
            print(f"Skipping {test_file} (file not found)")
    
    print("\n=== Test Complete ===")
