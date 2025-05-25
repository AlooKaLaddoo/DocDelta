# PDF Comparison Tool

A comprehensive PDF comparison tool that performs visual and textual analysis of PDF documents, highlighting differences with color-coded annotations.

## Features

- **Word-Level Comparison**: Detects changes at the word level for precise difference detection
- **Visual Annotations**: 
  - 🔴 Red background: Deletions (with preserved text visibility)
  - 🟢 Green background: Insertions
  - 🟠 Orange background: Modifications
- **HTML Report Generation**: Professional, responsive reports with side-by-side comparison
- **Page Padding**: Automatically handles PDFs with different page counts
- **Smart Text Comparison**: Layout-independent text analysis
- **Timestamped Output**: Each comparison saved in organized folders

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python doc_compare.py <file1.pdf> <file2.pdf>
```

### Example

```bash
python doc_compare.py 1_Comparison_Text.pdf 2_Comparison_Text.pdf
```

## Output

The tool creates a timestamped folder in `temp/` containing:
- `comparison_report.html` - Interactive HTML report
- `original_page_X.png` - Original pages from first PDF
- `modified_page_X.png` - Annotated pages showing differences

## Features

- Side-by-side page comparison
- Statistics summary (total changes, deletions, insertions, modifications)
- Navigation between pages
- Responsive design for different screen sizes
- Color-coded change indicators

## Dependencies

- PyMuPDF (fitz) >= 1.23.0 - PDF processing and text extraction
- Pillow >= 10.0.0 - Image processing and annotation