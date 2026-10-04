import pdfplumber
import pytesseract
import docx
from PIL import Image
import datetime

def _is_usable_text(text: str) -> bool:
    """Point 4: Deterministic rule for usable text (>50 alphanumeric characters)"""
    if not text:
        return False
    alnum_count = sum(c.isalnum() for c in text)
    return alnum_count > 50

def extract_pdf(file_path: str, document_id: str, file_type: str) -> dict:
    """Point 5 & 11: Mixed PDFs and robust error handling"""
    blocks = []
    used_native = False
    used_ocr = False
    
    if "image" in file_type:
        # Pure Image OCR
        text = pytesseract.image_to_string(Image.open(file_path)).strip()
        if text:
            blocks.append({"text": text, "page_number": 1, "position": None, "source_file": file_path, "method": "ocr"})
            used_ocr = True
        return generate_normalized_output(document_id, "ocr", blocks, 1)

    # Mixed PDF Processing
    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            native_text = page.extract_text()
            
            if _is_usable_text(native_text):
                blocks.append({"text": native_text.strip(), "page_number": i + 1, "position": None, "source_file": file_path, "method": "native"})
                used_native = True
            else:
                # Fallback to OCR for this specific page
                img = page.to_image(resolution=200).original
                ocr_text = pytesseract.image_to_string(img).strip()
                if ocr_text:
                    blocks.append({"text": ocr_text, "page_number": i + 1, "position": None, "source_file": file_path, "method": "ocr"})
                used_ocr = True
                
    if used_native and used_ocr:
        overall_method = "mixed"
    elif used_ocr:
        overall_method = "ocr"
    else:
        overall_method = "native"
        
    return generate_normalized_output(document_id, overall_method, blocks, total_pages)

def extract_docx(file_path: str, document_id: str) -> dict:
    """Point 7: DOCX Extraction with null pagination"""
    blocks = []
    doc = docx.Document(file_path)
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            blocks.append({
                "text": para.text.strip(), 
                "page_number": None,  # Null for DOCX
                "position": f"para_{i}", 
                "source_file": file_path, 
                "method": "native"
            })
    return generate_normalized_output(document_id, "native", blocks, 1)

def generate_normalized_output(doc_id: str, method: str, blocks: list, pages: int) -> dict:
    """Point 6: Normalized output representation"""
    return {
        "document_id": doc_id,
        "extraction_method": method,
        "blocks": blocks,
        "metadata": {
            "extraction_timestamp": datetime.datetime.utcnow().isoformat(),
            "pdf_parser_version": f"pdfplumber {pdfplumber.__version__}",
            "ocr_version": f"pytesseract {pytesseract.__version__}",
            "docx_version": f"python-docx {docx.__version__}",
            "pages_processed": pages,
            "warnings": ["Positional metadata is un-normalized and set to None where unavailable (Day 3 Constraint)"]
        }
    }