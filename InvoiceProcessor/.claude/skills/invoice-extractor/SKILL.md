---
name: invoice-extractor
description: "Extracts invoice number, date, supplier, total and VAT from invoice files (PDF or image) and outputs CSV or JSON. Use whenever the user asks to read, parse, extract or summarise data from an invoice or a folder of invoices."
argument-hint: <invoice file or folder> [csv|json]
arguments: [file, format]
---

# Extract Information From Invoice

Invoice file or folder: $file
Requested output format: $format

If no invoice file or folder was given, ask the user which invoice to process.

## Output format

- If the requested format is "json" (any capitalization), output JSON.
- If it is "csv" or empty, output CSV. CSV is the default.
- If it is anything else, tell the user the options are csv or json, then use CSV.
- If the skill was triggered without arguments and the user asked for JSON in their message, use JSON.

## What to extract

Extract the following from the invoice: Invoice Number, Invoice Date, Supplier Name, Total, VAT.

If a folder is supplied then extract all of the invoices in the folder. If a single file is supplied just extract the single invoice.

Add a sequence number for the number of the invoice in the folder. Use 1 if there is only a single invoice.

Add an "errors" entry for errors on the invoice. For example an invalid date or errors in calculations. Use a very short description of the error - "Invalid date 13/04/2026" is plenty, no need for further explanation.

Add a "notes" entry for other issues that aren't classed as errors. Include discrepancies, potential problems etc. Use short descriptions of the notes, no need for detailed explanations.

Do not add notes for things that are correct, for example there is no need to report that EUR is assumed for an Irish supplier.

If there is more than one error or note for an invoice, separate them with "; ".

Format all dates in dd/mm/yyyy format.

Format all numbers with 2 decimal places.

Assume EUR currency for any invoices with a supplier address in Ireland. Do not note this.

Any missing or null numeric values should be 0.00. Any missing text values should be empty.

<!--
this is a comment
VAT was producing a lot of irrelevant notes so explicitly ask
that they not be included
-->
There is no VAT on training, so there is no need to note anything about VAT for training invoices. For example, no need to say there is no VAT number, or to flag that there is a VAT number but VAT isn't included.

## CSV format

Output a header row followed by one row per invoice, with these columns in this order:

```
sequenceNo,invoiceNo,invoiceDate,supplierName,total,vat,errors,notes
1,INV-001,01/03/2026,Acme Ltd,1.99,0.55,,
2,INV-002,13/04/2026,"Smith, Jones & Co",120.00,27.60,Invalid date 13/04/2026,Total does not match line items
```

Wrap any value that contains a comma or a double quote in double quotes, and double any double quotes inside it.

## JSON format

Output a JSON list in this format:

```json
[
  {
    "sequenceNo": 1,
    "invoiceNo": "INV-001",
    "invoiceDate": "01/03/2026",
    "supplierName": "Acme Ltd",
    "total": 1.99,
    "vat": 0.55,
    "errors": "",
    "notes": ""
  },
  {
    "sequenceNo": 2,
    "invoiceNo": "INV-002",
    "invoiceDate": "13/04/2026",
    "supplierName": "Smith, Jones & Co",
    "total": 120.00,
    "vat": 27.60,
    "errors": "Invalid date 13/04/2026",
    "notes": "Total does not match line items"
  }
]
```

## Validate before output

Every run must be validated. Do not show the result to the user until it passes.

1. Write the extracted data to `invoice-output.csv` (or `invoice-output.json` for JSON
   output) in the current working directory, overwriting any previous run.
2. Run the validator against that file:

   ```
   python "<skill directory>/scripts/validate_output.py" invoice-output.csv
   ```

   Add `--format csv` or `--format json` if the file does not use the matching extension.
3. The script exits 0 when the file is valid, 1 when it reports `ERROR:` lines, and 2 when
   the file is missing or cannot be parsed.
4. If it fails, fix the file (re-reading the invoices if a value is actually wrong, not just
   the formatting) and run it again. Repeat until it exits 0.
5. `WARN:` lines do not fail the run. They flag an empty invoice number, supplier or date -
   check the invoice once to confirm the value really is absent, then carry on.

The validator checks structure only: that all eight fields are present and in order, that
`sequenceNo` runs 1..n, that dates are dd/mm/yyyy, and that `total` and `vat` are numbers
with 2 decimal places. It does not check that the values match the invoice - that is still
your job. It deliberately accepts dates like 31/04/2026 that are well formed but impossible,
because those belong in the "errors" field rather than failing the run.

## Final output

Print the contents of the validated file. Only output the CSV or JSON, do not output
anything else. Put errors in the "errors" field and notes in the "notes" field.
