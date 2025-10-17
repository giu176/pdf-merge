from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
import sys

def merge_pdf(template_pdf, input_pdf, output_pdf):
    # Apri i PDF con PyMuPDF
    template_doc = fitz.open(template_pdf)
    input_doc = fitz.open(input_pdf)
    
    # Crea un nuovo documento PDF
    writer = fitz.open()
    
    # Aggiungi tutte le pagine del template
    for page in template_doc:
        writer.insert_pdf(template_doc, from_page=page.number, to_page=page.number)
    
    # Ottieni l'ultima pagina del template per usarla come sfondo
    last_template_page = template_doc[-1]
    last_template_rect = last_template_page.rect
    
    # Aggiungi le pagine di input.pdf (ignorando la prima)
    for i in range(1, len(input_doc)):
        input_page = input_doc[i]
        input_rect = input_page.rect
        
        # Crea una nuova pagina basata sulla copia dell'ultima pagina del template
        new_page = writer.new_page(width=last_template_rect.width, height=last_template_rect.height)
        new_page.show_pdf_page(last_template_rect, template_doc, len(template_doc) - 1)
        
        # Calcola il ridimensionamento mantenendo le proporzioni e scalando del 85%
        scale_x = (last_template_rect.width / input_rect.width) * 0.80
        scale_y = (last_template_rect.height / input_rect.height) * 0.80
        scale = min(scale_x, scale_y)  # Mantiene le proporzioni senza distorsioni
        
        new_width = input_rect.width * scale
        new_height = input_rect.height * scale
        
        # Calcola il posizionamento centrato tra intestazione e piè di pagina
        x_offset = (last_template_rect.width - new_width) / 2
        y_offset = (last_template_rect.height - new_height) / 2
        
        # Inserisci la pagina ridimensionata
        new_page.show_pdf_page(
            fitz.Rect(x_offset, y_offset, x_offset + new_width, y_offset + new_height),
            input_doc,
            i
        )
    
    # Rimuovi l'ultima pagina che era stata aggiunta dal template
    writer.delete_page(len(template_doc) - 1)
    
    # Salva il nuovo PDF
    writer.save(output_pdf)
    writer.close()
    
    print(f"Documento PDF creato: {output_pdf}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Uso: python script.py template.pdf input.pdf output.pdf")
    else:
        merge_pdf(sys.argv[1], sys.argv[2], sys.argv[3])
