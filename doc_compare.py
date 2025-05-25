#!/usr/bin/env python3
import os
import sys
import argparse
from datetime import datetime
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import difflib
from jinja2 import Template
from fuzzywuzzy import fuzz
from docx import Document
from fpdf import FPDF
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# pip install -r requirements.txt
# sudo dnf install tesseract

class PDFComparer:
    def _convert_docx_to_pdf(self, docx_path, output_pdf_path):
        """Convert a .docx file to a PDF file."""
        try:
            logging.info(f"Converting {docx_path} to PDF...")

            # Load the .docx file
            doc = Document(docx_path)

            # Create a PDF object
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)

            # Add content from the .docx file to the PDF
            for paragraph in doc.paragraphs:
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 10, paragraph.text)

            # Save the PDF
            pdf.output(output_pdf_path)
            logging.info(f"Converted {docx_path} to {output_pdf_path}")
        except Exception as e:
            logging.error(f"Error converting {docx_path} to PDF: {e}")
            raise

    def _ensure_pdf(self, file_path):
        """Ensure the input file is a PDF. If not, convert it to PDF."""
        try:
            if file_path.lower().endswith('.pdf'):
                return file_path  # Already a PDF

            if file_path.lower().endswith('.docx'):
                # Convert .docx to PDF
                output_pdf_path = file_path.rsplit('.', 1)[0] + '.pdf'
                self._convert_docx_to_pdf(file_path, output_pdf_path)
                return output_pdf_path

            raise ValueError(f"Unsupported file format: {file_path}. Only .pdf and .docx are supported.")
        except Exception as e:
            logging.error(f"Error ensuring PDF format for {file_path}: {e}")
            raise

    def _pad_images(self, images, target_count, size):
        """Pad a list of images with blank pages to match the target count."""
        blank = Image.new('RGB', size, (255, 255, 255))
        for _ in range(target_count - len(images)):
            images.append(blank.copy())

    def __init__(self, pdf1_path, pdf2_path, output_dir=None, dpi=300):
        """
        Initialize with paths to two files to compare (PDF or DOCX).
        
        Args:
            pdf1_path (str): Path to the first file (PDF or DOCX)
            pdf2_path (str): Path to the second file (PDF or DOCX)
            output_dir (str): Directory to save results (default creates timestamp folder)
            dpi (int): DPI for PDF to image conversion (higher means better quality but slower)
        """
        try:
            # Ensure both files are PDFs
            self.pdf1_path = self._ensure_pdf(pdf1_path)
            self.pdf2_path = self._ensure_pdf(pdf2_path)
            
            # Create output directory with timestamp if not specified
            if output_dir is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.output_dir = os.path.join("fileComparison", f"pdf_diff_{timestamp}")
            else:
                self.output_dir = output_dir
                
            self.image_dir = os.path.join(self.output_dir, "images")
            self.dpi = dpi
            
            # Create output directories
            os.makedirs(self.output_dir, exist_ok=True)
            os.makedirs(self.image_dir, exist_ok=True)
            
            # Store text and image data
            self.pdf1_images = []
            self.pdf2_images = []
            self.pdf1_text = []
            self.pdf2_text = []
            self.diff_images = []
            self.word_diff_images = []
            self.visual_diff_images = []
        except Exception as e:
            logging.error(f"Error initializing PDFComparer: {e}")
            raise
        
    def convert_pdfs_to_images(self):
        """Convert both PDFs to images for processing"""
        try:
            logging.info(f"Converting {os.path.basename(self.pdf1_path)} to images...")
            self.pdf1_images = convert_from_path(self.pdf1_path, dpi=self.dpi)

            logging.info(f"Converting {os.path.basename(self.pdf2_path)} to images...")
            self.pdf2_images = convert_from_path(self.pdf2_path, dpi=self.dpi)

            # Handle case where PDFs have different page counts
            max_pages = max(len(self.pdf1_images), len(self.pdf2_images))
            logging.info(f"PDF 1 has {len(self.pdf1_images)} pages, PDF 2 has {len(self.pdf2_images)} pages")

            # Pad the shorter PDF with blank pages
            if len(self.pdf1_images) < max_pages:
                self._pad_images(self.pdf1_images, max_pages, self.pdf1_images[0].size)

            if len(self.pdf2_images) < max_pages:
                self._pad_images(self.pdf2_images, max_pages, self.pdf2_images[0].size)
        except Exception as e:
            logging.error(f"Error converting PDFs to images: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from a PDF file using pdfplumber."""
        try:
            import pdfplumber
            logging.info(f"Extracting text from {os.path.basename(pdf_path)}...")

            text_pages = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    text_pages.append(text)

            return text_pages
        except Exception as e:
            logging.error(f"Error extracting text from {pdf_path}: {e}")
            raise

    def apply_text_extraction(self):
        """Extract text from both PDFs directly."""
        try:
            logging.info("Extracting text from PDFs...")
            self.pdf1_text = self.extract_text_from_pdf(self.pdf1_path)
            self.pdf2_text = self.extract_text_from_pdf(self.pdf2_path)
        except Exception as e:
            logging.error(f"Error during text extraction: {e}")
            raise

    def find_word_differences(self, text1, text2, by_line=False):
        """
        Find differences between two text strings using Myers' algorithm (via difflib.SequenceMatcher).
        If by_line is True, compare line by line; otherwise, compare word by word.
        Returns:
            dict: Contains 'insertions', 'deletions', and 'modifications' lists
        """
        import string
        def normalize(s):
            # Lowercase, strip, and remove punctuation for better matching
            return s.lower().strip().translate(str.maketrans('', '', string.punctuation))

        if by_line:
            seq1 = [normalize(line) for line in text1.splitlines() if line.strip()]
            seq2 = [normalize(line) for line in text2.splitlines() if line.strip()]
        else:
            seq1 = [normalize(word) for word in text1.split() if word.strip()]
            seq2 = [normalize(word) for word in text2.split() if word.strip()]

        matcher = difflib.SequenceMatcher(None, seq1, seq2, autojunk=False)
        insertions = []
        deletions = []
        modifications = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                for i in range(i1, i2):
                    if i < len(seq1):
                        deletions.append(seq1[i])
                for j in range(j1, j2):
                    if j < len(seq2):
                        insertions.append(seq2[j])
                mod_len = min(i2 - i1, j2 - j1)
                for k in range(mod_len):
                    if i1 + k < len(seq1) and j1 + k < len(seq2):
                        modifications.append((seq1[i1 + k], seq2[j1 + k]))
            elif tag == 'delete':
                for i in range(i1, i2):
                    if i < len(seq1):
                        deletions.append(seq1[i])
            elif tag == 'insert':
                for j in range(j1, j2):
                    if j < len(seq2):
                        insertions.append(seq2[j])

        return {
            'insertions': insertions,
            'deletions': deletions,
            'modifications': modifications
        }

    def _highlight_differences(self, ocr_data, target_words, color, image):
        """Highlight differences on an image based on OCR data."""
        matches = self._filter_matches(ocr_data, target_words)
        for i, _, _ in matches:
            x, y, w, h = (
                ocr_data['left'][i],
                ocr_data['top'][i],
                ocr_data['width'][i],
                ocr_data['height'][i]
            )
            if w > 0 and h > 0 and x >= 0 and y >= 0:
                cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
                overlay = image.copy()
                cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
                cv2.addWeighted(overlay, 0.3, image, 0.7, 0, image)

    def _filter_matches(self, ocr_data, target_words, min_confidence=40):
        """Filter OCR matches based on confidence and target words."""
        matches = []
        for i, word in enumerate(ocr_data['text']):
            if word and word.strip():
                confidence = ocr_data['conf'][i]
                if confidence >= min_confidence:
                    for target in target_words:
                        if target.strip() and (target == word or fuzz.ratio(target.lower(), word.lower()) > 85):
                            matches.append((i, target, word))
                            break
        return matches

    def create_annotated_images(self):
        """Create annotated images showing the differences"""
        try:
            logging.info("Creating annotated comparison images...")

            for page_num in range(len(self.pdf1_images)):
                logging.info(f"Processing page {page_num+1}/{len(self.pdf1_images)}...")

                img1 = self.pdf1_images[page_num].copy()
                img2 = self.pdf2_images[page_num].copy()

                img1_cv = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2BGR)
                img2_cv = cv2.cvtColor(np.array(img2), cv2.COLOR_RGB2BGR)

                diff_dict = self.find_word_differences(self.pdf1_text[page_num], self.pdf2_text[page_num])

                left_img_path = os.path.join(self.image_dir, f"left_{page_num}.png")
                right_img_path = os.path.join(self.image_dir, f"right_{page_num}.png")
                img1.save(left_img_path)
                img2.save(right_img_path)

                h1, w1 = img1_cv.shape[:2]
                h2, w2 = img2_cv.shape[:2]
                max_h = max(h1, h2)
                diff_img = np.ones((max_h, w1 + w2 + 10, 3), dtype=np.uint8) * 255

                diff_img[:h1, :w1] = img1_cv
                diff_img[:h2, w1+10:] = img2_cv
                cv2.line(diff_img, (w1+5, 0), (w1+5, max_h), (100, 100, 100), 2)

                word_diff_img1 = img1_cv.copy()
                word_diff_img2 = img2_cv.copy()

                ocr_data1 = pytesseract.image_to_data(img1, output_type=pytesseract.Output.DICT)
                ocr_data2 = pytesseract.image_to_data(img2, output_type=pytesseract.Output.DICT)

                self._highlight_differences(ocr_data1, diff_dict['deletions'], (0, 0, 255), word_diff_img1)
                self._highlight_differences(ocr_data2, diff_dict['insertions'], (0, 255, 0), word_diff_img2)

                for old_word, new_word in diff_dict['modifications']:
                    self._highlight_differences(ocr_data1, [old_word], (0, 165, 255), word_diff_img1)
                    self._highlight_differences(ocr_data2, [new_word], (0, 165, 255), word_diff_img2)

                word_diff_combined = np.ones((max_h, w1 + w2 + 10, 3), dtype=np.uint8) * 255
                word_diff_combined[:h1, :w1] = word_diff_img1
                word_diff_combined[:h2, w1+10:] = word_diff_img2
                cv2.line(word_diff_combined, (w1+5, 0), (w1+5, max_h), (100, 100, 100), 2)

                diff_path = os.path.join(self.image_dir, f"diff_{page_num}.png")
                word_diff_path = os.path.join(self.image_dir, f"word_diff_{page_num}.png")

                cv2.imwrite(diff_path, diff_img)
                cv2.imwrite(word_diff_path, word_diff_combined)

                self.diff_images.append(diff_path)
                self.word_diff_images.append(word_diff_path)
        except Exception as e:
            logging.error(f"Error creating annotated images: {e}")
            raise
    
    def create_visual_diff_images(self):
        """Create pixel-by-pixel visual diff images for each page."""
        try:
            logging.info("Creating pixel-by-pixel visual diff images...")
            self.visual_diff_images = []
            for page_num in range(len(self.pdf1_images)):
                img1 = self.pdf1_images[page_num].copy()
                img2 = self.pdf2_images[page_num].copy()
                img1_cv = cv2.cvtColor(np.array(img1), cv2.COLOR_RGB2BGR)
                img2_cv = cv2.cvtColor(np.array(img2), cv2.COLOR_RGB2BGR)

                # Ensure same size
                h = max(img1_cv.shape[0], img2_cv.shape[0])
                w = max(img1_cv.shape[1], img2_cv.shape[1])
                def pad_img(img, h, w):
                    pad_h = h - img.shape[0]
                    pad_w = w - img.shape[1]
                    return cv2.copyMakeBorder(img, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=[255,255,255])
                img1_cv = pad_img(img1_cv, h, w)
                img2_cv = pad_img(img2_cv, h, w)

                # Compute absolute difference
                diff = cv2.absdiff(img1_cv, img2_cv)
                # Highlight differences in magenta (where diff is significant)
                gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                _, mask = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY)
                visual_diff = img2_cv.copy()
                visual_diff[mask > 0] = [255, 0, 255]  # Magenta for changed pixels
                # Overlay magenta on top of img2
                overlay = img2_cv.copy()
                overlay[mask > 0] = [255, 0, 255]
                cv2.addWeighted(overlay, 0.5, img2_cv, 0.5, 0, visual_diff)

                visual_diff_path = os.path.join(self.image_dir, f"visual_diff_{page_num}.png")
                cv2.imwrite(visual_diff_path, visual_diff)
                self.visual_diff_images.append(visual_diff_path)
        except Exception as e:
            logging.error(f"Error creating visual diff images: {e}")
            raise

    def generate_html_report(self):
        """Generate an HTML report with the comparison results, including a summary of changes and visual diffs."""
        try:
            html_template = """
            <!DOCTYPE html>
            <html lang=\"en\">
            <head>
                <meta charset=\"UTF-8\">
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                <title>PDF Comparison Report</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                        background-color: #f5f5f5;
                    }
                    .header {
                        background-color: #333;
                        color: white;
                        padding: 20px;
                        text-align: center;
                    }
                    .container {
                        max-width: 1600px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .summary {
                        background-color: white;
                        border-radius: 5px;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        margin-bottom: 30px;
                        padding: 20px;
                    }
                    .comparison-section {
                        background-color: white;
                        border-radius: 5px;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        margin-bottom: 30px;
                        padding: 20px;
                    }
                    .page-title {
                        background-color: #f0f0f0;
                        padding: 10px;
                        margin-bottom: 20px;
                        border-radius: 3px;
                        text-align: center;
                    }
                    .diff-view, .word-diff-view, .visual-diff-view {
                        margin-bottom: 30px;
                    }
                    .tabs {
                        display: flex;
                        margin-bottom: 10px;
                        border-bottom: 1px solid #ddd;
                    }
                    .tab {
                        padding: 10px 20px;
                        cursor: pointer;
                        background-color: #f1f1f1;
                        border: 1px solid #ddd;
                        border-bottom: none;
                        border-radius: 5px 5px 0 0;
                        margin-right: 5px;
                    }
                    .tab.active {
                        background-color: white;
                    }
                    .tab-content {
                        display: none;
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-top: none;
                    }
                    .tab-content.active {
                        display: block;
                    }
                    img {
                        max-width: 100%;
                        height: auto;
                    }
                    .legend {
                        margin-top: 10px;
                        padding: 10px;
                        background-color: #f9f9f9;
                        border-radius: 3px;
                    }
                    .legend-item {
                        display: inline-block;
                        margin-right: 20px;
                    }
                    .color-box {
                        display: inline-block;
                        width: 15px;
                        height: 15px;
                        margin-right: 5px;
                        vertical-align: middle;
                    }
                    .file-info {
                        display: flex;
                        justify-content: space-between;
                        background-color: #eee;
                        padding: 10px;
                        border-radius: 3px;
                        margin-bottom: 20px;
                    }
                    .file-name {
                        font-weight: bold;
                    }
                </style>
            </head>
            <body>
                <div class=\"header\">
                    <h1>PDF Comparison Report</h1>
                    <p>Generated on {{ timestamp }}</p>
                </div>
                
                <div class=\"container\">
                    <div class=\"file-info\">
                        <div class=\"file-name\">Left PDF: {{ pdf1_name }}</div>
                        <div class=\"file-name\">Right PDF: {{ pdf2_name }}</div>
                    </div>

                    <div class=\"summary\">
                        <h2>Summary of Changes</h2>
                        <ul>
                            {% for change in changes %}
                            <li>{{ change }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    
                    <div class=\"legend\">
                        <h3>Legend</h3>
                        <div class=\"legend-item\"><span class=\"color-box\" style=\"background-color: rgba(0,255,0,0.3);\"></span> Added text (green)</div>
                        <div class=\"legend-item\"><span class=\"color-box\" style=\"background-color: rgba(255,0,0,0.3);\"></span> Deleted text (red)</div>
                        <div class=\"legend-item\"><span class=\"color-box\" style=\"background-color: rgba(255,165,0,0.3);\"></span> Modified text (orange)</div>
                        <div class=\"legend-item\"><span class=\"color-box\" style=\"background-color: rgba(255,0,255,0.3);\"></span> Visual diff (magenta overlay)</div>
                    </div>
                    
                    {% for page_num in range(total_pages) %}
                    <div class=\"comparison-section\">
                        <div class=\"page-title\">
                            <h2>Page {{ page_num + 1 }}</h2>
                        </div>
                        
                        <div class=\"tabs\">
                            <div class=\"tab active\" onclick=\"showTab({{ page_num }}, 'word-diff')\">Word Differences</div>
                            <div class=\"tab\" onclick=\"showTab({{ page_num }}, 'diff')\">Side by Side</div>
                            <div class=\"tab\" onclick=\"showTab({{ page_num }}, 'visual-diff')\">Visual Diff</div>
                        </div>
                        
                        <div class=\"tab-content active\" id=\"tab-{{ page_num }}-word-diff\">
                            <div class=\"word-diff-view\">
                                <img src=\"{{ word_diff_images[page_num] }}\" alt=\"Word difference view for page {{ page_num + 1 }}\">
                            </div>
                        </div>
                        
                        <div class=\"tab-content\" id=\"tab-{{ page_num }}-diff\">
                            <div class=\"diff-view\">
                                <img src=\"{{ diff_images[page_num] }}\" alt=\"Side by side difference view for page {{ page_num + 1 }}\">
                            </div>
                        </div>

                        <div class=\"tab-content\" id=\"tab-{{ page_num }}-visual-diff\">
                            <div class=\"visual-diff-view\">
                                <img src=\"{{ visual_diff_images[page_num] }}\" alt=\"Visual diff for page {{ page_num + 1 }}\">
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                <script>
                    function showTab(pageNum, tabName) {
                        // Hide all tab contents
                        const tabContents = document.querySelectorAll(`[id^=\"tab-${pageNum}-\"]`);
                        tabContents.forEach(content => {
                            content.classList.remove('active');
                        });
                        
                        // Show selected tab content
                        const selectedTab = document.getElementById(`tab-${pageNum}-${tabName}`);
                        selectedTab.classList.add('active');
                        
                        // Update tab buttons
                        const tabs = selectedTab.parentElement.previousElementSibling.children;
                        for (let i = 0; i < tabs.length; i++) {
                            tabs[i].classList.remove('active');
                        }
                        let clickedTabIndex = 0;
                        if (tabName === 'word-diff') clickedTabIndex = 0;
                        else if (tabName === 'diff') clickedTabIndex = 1;
                        else if (tabName === 'visual-diff') clickedTabIndex = 2;
                        tabs[clickedTabIndex].classList.add('active');
                    }
                </script>
            </body>
            </html>
            """
            # Prepare data for template
            changes = []
            for page_num in range(len(self.pdf1_text)):
                diff_dict = self.find_word_differences(self.pdf1_text[page_num], self.pdf2_text[page_num])
                if diff_dict['insertions']:
                    changes.append(f"Page {page_num + 1}: {len(diff_dict['insertions'])} insertions.")
                if diff_dict['deletions']:
                    changes.append(f"Page {page_num + 1}: {len(diff_dict['deletions'])} deletions.")
                if diff_dict['modifications']:
                    changes.append(f"Page {page_num + 1}: {len(diff_dict['modifications'])} modifications.")
            template_data = {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'pdf1_name': os.path.basename(self.pdf1_path),
                'pdf2_name': os.path.basename(self.pdf2_path),
                'total_pages': len(self.pdf1_images),
                'diff_images': [os.path.relpath(path, self.output_dir) for path in self.diff_images],
                'word_diff_images': [os.path.relpath(path, self.output_dir) for path in self.word_diff_images],
                'visual_diff_images': [os.path.relpath(path, self.output_dir) for path in self.visual_diff_images],
                'changes': changes
            }
            # Generate HTML
            template = Template(html_template)
            html_content = template.render(**template_data)
            # Write to file
            html_path = os.path.join(self.output_dir, "pdf_diff.html")
            with open(html_path, 'w') as f:
                f.write(html_content)
            logging.info(f"\nComparison complete! HTML report generated at: {html_path}")
            return html_path
        except Exception as e:
            logging.error(f"Error generating HTML report: {e}")
            raise
    
    def process(self):
        """Process the PDFs and generate comparison"""
        try:
            logging.info(f"Starting PDF comparison: {os.path.basename(self.pdf1_path)} vs {os.path.basename(self.pdf2_path)}")
            # Main workflow
            self.convert_pdfs_to_images()
            self.apply_text_extraction()  # Use direct text extraction instead of OCR
            self.create_annotated_images()
            self.create_visual_diff_images()
            return self.generate_html_report()
        except Exception as e:
            logging.error(f"Error during PDF comparison process: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Compare two files (PDF or DOCX) and generate a visual diff report')
    parser.add_argument('file1', help='Path to the first file (PDF or DOCX)')
    parser.add_argument('file2', help='Path to the second file (PDF or DOCX)')
    parser.add_argument('-o', '--output', help='Output directory for comparison results')
    parser.add_argument('-d', '--dpi', type=int, default=300, help='DPI for PDF to image conversion (higher is better quality but slower)')

    args = parser.parse_args()

    # Check if files exist
    if not os.path.isfile(args.file1):
        logging.error(f"Error: File not found: {args.file1}")
        return 1

    if not os.path.isfile(args.file2):
        logging.error(f"Error: File not found: {args.file2}")
        return 1

    # Run comparison
    try:
        comparer = PDFComparer(args.file1, args.file2, args.output, args.dpi)
        html_path = comparer.process()

        logging.info(f"Success! Report saved to: {html_path}")
        logging.info(f"Open this file in a web browser to view the comparison.")
        return 0
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())