import os
import torch
import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class SummarizerEngine:
    def __init__(self):
        self.model_name = os.getenv("MODEL_NAME", "t5-small")
        logging.info(f"Loading local summarization model: '{self.model_name}'...")
        
        # Directly load tokenizer and Seq2Seq model (compatible with Transformers v4 and v5)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        self.model.eval()
        logging.info("Model loaded successfully into memory.")

    def _chunk_text(self, text: str, max_words_per_chunk: int = 400) -> list[str]:
        words = text.split()
        if not words:
            return []
        chunks = []
        for i in range(0, len(words), max_words_per_chunk):
            chunks.append(" ".join(words[i:i + max_words_per_chunk]))
        return chunks

    def summarize(self, text: str) -> str:
        if not text.strip():
            return "No text provided for summarization."

        chunks = self._chunk_text(text, max_words_per_chunk=350)
        chunk_summaries = []

        logging.info(f"Summarizing document in {len(chunks)} chunk(s)...")

        for chunk in chunks:
            # T5 models expect a 'summarize: ' prefix
            prefix = "summarize: " if "t5" in self.model_name.lower() else ""
            input_text = prefix + chunk

            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                max_length=512,
                truncation=True
            )

            with torch.no_grad():
                summary_ids = self.model.generate(
                    inputs["input_ids"],
                    max_length=150,
                    min_length=20,
                    num_beams=2,
                    length_penalty=2.0,
                    early_stopping=True
                )

            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            chunk_summaries.append(summary)

        return " ".join(chunk_summaries)
