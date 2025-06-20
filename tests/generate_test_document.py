from src.generators.document_generator import DocumentGenerator

generator = DocumentGenerator()
test_data = generator.generate_test_data()
output_path = generator.generate_pdf(test_data)
print(f"Documento generado: {output_path}")