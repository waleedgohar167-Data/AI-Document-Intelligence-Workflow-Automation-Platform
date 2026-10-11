import os
from fpdf import FPDF

DATASET_DIR = "evaluation_dataset"
os.makedirs(DATASET_DIR, exist_ok=True)

def create_pdf(filename, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=content)
    pdf.output(f"{DATASET_DIR}/{filename}")

print("Generating synthetic evaluation dataset...")

# 1. Valid Invoice PDF
create_pdf("1_valid_invoice.pdf", "INVOICE #1001\nDate: 2026-10-12\nTotal Amount: 500.00\nTax Amount: 50.00\nSubtotal: 450.00\nPlease pay this invoice within 30 days.")

# 2. Valid Contract PDF
create_pdf("2_valid_contract.pdf", "MASTER SERVICE AGREEMENT\nEffective Date: 2026-10-12\nParty A: Tech Corp\nParty B: Client LLC\nAuto Renewing: True\nTerms and conditions apply to this contract.")

# 3. Valid Receipt PDF
create_pdf("3_valid_receipt.pdf", "RECEIPT\nMerchant: Uber\nTransaction Date: 2026-10-11\nTotal Amount: 25.50\nPayment Method: CREDIT")

# 4. Noise File (Fails Day 4 Classification)
create_pdf("4_noise_email.pdf", "Hey team, just following up on the project status. Let me know when the meeting is scheduled. Thanks!")

# 5. Malicious File (Fails Day 2 MIME Validation)
# This is a text file masquerading as a PDF to prove your Day 2 security works
with open(f"{DATASET_DIR}/5_malicious_fake.pdf", "w") as f:
    f.write("This is a plain text file, not a real PDF byte sequence. It should be rejected by the ingest endpoint.")

print(f"Success! 5 test documents generated in '{DATASET_DIR}'.")