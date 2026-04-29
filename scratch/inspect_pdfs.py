import sys
from pypdf import PdfReader

def extract(path):
    print(f"\n--- FILE: {path} ---")
    try:
        reader = PdfReader(path)
        for i, page in enumerate(reader.pages):
            print(f"PAGE {i+1}:")
            print(page.extract_text())
    except Exception as e:
        print(f"ERROR: {e}")

files = [
    "c:/Users/makim/OneDrive/Escritorio/Neuro_Flow/03_PROJECTS/BrunoBot/datos casa antigua/001581655_23751610_27042026.PDF",
    "c:/Users/makim/OneDrive/Escritorio/Neuro_Flow/03_PROJECTS/BrunoBot/datos casa antigua/32429009.pdf",
    "c:/Users/makim/OneDrive/Escritorio/Neuro_Flow/03_PROJECTS/BrunoBot/datos casa antigua/CierrePos.pdf"
]

for f in files:
    extract(f)
