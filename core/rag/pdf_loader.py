from pypdf import PdfReader

from .document import Document


class PDFLoader:

    def load(self, file_path: str) -> list[Document]:

        reader = PdfReader(file_path)

        documents = []

        for page_number, page in enumerate(reader.pages, start=1):

            text = page.extract_text()

            if text and text.strip():

                documents.append(
                    Document(
                        content=text.strip(),
                        source=file_path,
                        page=page_number
                    )
                )

        return documents