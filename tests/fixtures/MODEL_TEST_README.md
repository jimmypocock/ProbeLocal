# Model Testing with Unified Document Store

## How Model Tests Work Now

The app has changed from individual document uploads to a unified document store approach:

1. **Old approach**: Upload documents individually, get separate document IDs
2. **New approach**: All documents in `/documents` folder are preprocessed at startup into a unified vector store

## Running Model Tests

### Quick Test
```bash
make test-models-quick
```
This runs a quick test to see if the model can differentiate between the current documents in the unified store.

### Full Model Test
```bash
make test-models MODELS='mistral,llama3'
```
This:
1. Copies test documents to `/documents` folder
2. Prompts you to restart the app (to process the documents)
3. Tests how well each model can differentiate between documents
4. Asks questions that require identifying information from specific documents

## Test Questions

The tests ask questions like:
- "What is the invoice number in the Excel file?" (should find INV-2025-006)
- "What company sent the invoice in the Markdown file?" (should find CloudScale)
- "Which invoice has the highest total amount?" (tests comparison across documents)

## Why This Matters

With a unified vector store, the challenge is whether the model can:
1. Retrieve the right chunks from the right documents
2. Not mix up information between similar documents (multiple invoices, multiple stories)
3. Answer comparison questions that require understanding multiple documents

## Test Documents

The test suite includes multiple versions of similar content:
- **Invoices**: Different companies, amounts, and invoice numbers in Excel, Markdown, and Word formats
- **Stories**: Different narratives in Excel, Markdown, and Word formats

This tests whether the RAG system and model can maintain document boundaries even when all documents are in the same vector store.