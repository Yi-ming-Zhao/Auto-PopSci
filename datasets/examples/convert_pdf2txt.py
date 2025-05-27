import fitz  # PyMuPDF
import sys


def pdf_to_text(pdf_path, txt_path):
    doc = fitz.open(pdf_path)
    with open(txt_path, "w", encoding="utf-8") as f:
        for page in doc:
            f.write(page.get_text())
            f.write("\n\n")
    print(f"✅ Saved to {txt_path}")


if __name__ == "__main__":
    # 替换成你的 PDF 路径
    pdf_path = "datasets/examples/FineSurE Fine-grained Summarization Evaluation using LLMs.pdf"
    txt_path = "datasets/examples/FineSurE Fine-grained Summarization Evaluation using LLMs.txt"
    pdf_to_text(pdf_path, txt_path)
