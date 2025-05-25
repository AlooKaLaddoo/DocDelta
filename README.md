# Document Comparison Tool

A comprehensive document comparison tool that performs visual and textual analysis of various document formats (PDF, DOCX, XLSX, PPTX), highlighting differences with color-coded annotations.

## Features

- **Multi-Format Support**: Compare PDF, DOCX, XLSX, and PPTX files
- **Automatic Conversion**: Non-PDF documents are automatically converted to PDF for comparison
- **Word-Level Comparison**: Detects changes at the word level for precise difference detection
- **Visual Annotations**: 
  - 🔴 Red background: Deletions (with preserved text visibility)
  - 🟢 Green background: Insertions
  - 🟠 Orange background: Modifications
- **HTML Report Generation**: Professional, responsive reports with side-by-side comparison
- **Page Padding**: Automatically handles documents with different page counts
- **Smart Text Comparison**: Layout-independent text analysis
- **Timestamped Output**: Each comparison saved in organized folders

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python doc_compare.py <file1> <file2>
```

### Examples

```bash
# Compare PDF files
python doc_compare.py document1.pdf document2.pdf

# Compare Word documents
python doc_compare.py document1.docx document2.docx

# Compare Excel spreadsheets
python doc_compare.py spreadsheet1.xlsx spreadsheet2.xlsx

# Compare PowerPoint presentations
python doc_compare.py presentation1.pptx presentation2.pptx

# Mixed format comparison
python doc_compare.py document1.docx document2.pdf
```

## Output

The tool creates a timestamped folder in `temp/` containing:
- `comparison_report.html` - Interactive HTML report
- `original_page_X.png` - Original pages from first document
- `modified_page_X.png` - Annotated pages showing differences
- `temp_conversions/` - Intermediate PDF files (for non-PDF inputs)

## Features

- Side-by-side page comparison
- Statistics summary (total changes, deletions, insertions, modifications)
- Navigation between pages
- Responsive design for different screen sizes
- Color-coded change indicators

## Dependencies

### Core Dependencies
- PyMuPDF (fitz) >= 1.23.0 - PDF processing and text extraction
- Pillow >= 10.0.0 - Image processing and annotation

### Document Format Support
- python-docx - DOCX file processing
- openpyxl - XLSX file processing  
- python-pptx - PPTX file processing
- reportlab - PDF generation from other formats
- xlsxwriter - Additional Excel support