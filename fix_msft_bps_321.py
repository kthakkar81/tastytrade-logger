"""
One-off reconciliation for the MSFT 8/21 430/410 Bull Put Spread (row 321).

On 7/21 Kevin unwound the residual 1-ct spread leg-by-leg:
  - Closed the LONG $410P for a gain (Sell to Close @ 26.25)
  - ROLLED the SHORT $430P out+down to $425P 9/18 (BTC $430P + STO $425P)

The logger can't match either close because row 321 is a combined spread, not
two standalone legs. This script splits the position the way it was actually
traded:

  1. Convert row 321 in place  -> CLOSED CSP (short $430P), closed by the roll's BTC
  2. Insert a new row          -> CLOSED long Put ($410P), closed for a gain
  3. Clear the $410P entry from the Import Errors sheet

Per-leg economics come from the original 6/2 fills (2 ct, halved) and the 7/21
closes, using the same net-value / sign / PnL=K+L conventions as the logger.
"""
from spreadsheet_logger import SpreadsheetLogger
import config

# ---- computed leg economics (net-value based, per 1 contract) -------------
# 6/2 open:  STO 2x $430P net 4181.653 -> 2090.83/ct ; BTO 2x $410P net 2726.25 -> 1363.13/ct
# 7/21 close: BTC 1x $430P net 3967.12 (debit) ; STC 1x $410P net 2624.817 (credit)
CSP_OPEN_CREDIT   = 2090.83
CSP_CLOSE_DEBIT   = -3967.12          # BTC -> negative (debit), same as existing rows
CSP_FEES          = 1.29              # open 1.17 + close 0.12
CSP_PNL           = round(CSP_OPEN_CREDIT + CSP_CLOSE_DEBIT, 2)   # -1876.29

PUT_OPEN_DEBIT    = -1363.13          # long put paid -> negative opening net
PUT_CLOSE_CREDIT  = 2624.82           # STC -> positive credit
PUT_FEES          = 1.31              # open 1.13 + close 0.18
PUT_PNL           = round(PUT_OPEN_DEBIT + PUT_CLOSE_CREDIT, 2)   # 1261.69

CLOSE_DATE = "7/21/2026"


def show(sheet, r):
    v = sheet.get(f"A{r}:P{r}", value_render_option="FORMATTED_VALUE")
    print(f"  Row {r}: {v[0] if v else '(empty)'}")


def main():
    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        return 1
    sheet = logger.sheet
    ss = sheet.spreadsheet

    print("\n=== BEFORE ===")
    show(sheet, 321)

    # --- 1. Convert row 321 -> closed CSP (short $430P) --------------------
    sheet.batch_update([
        {'range': 'B321', 'values': [[CLOSE_DATE]]},        # Closing Date
        {'range': 'D321', 'values': [['CSP']]},             # Strategy Type
        {'range': 'E321', 'values': [['Closed']]},          # Status
        {'range': 'H321', 'values': [['']]},                # Long Strike -> clear
        {'range': 'J321', 'values': [[CSP_FEES]]},          # Fees (cumulative)
        {'range': 'K321', 'values': [[CSP_OPEN_CREDIT]]},   # Opening Net Price
        {'range': 'L321', 'values': [[CSP_CLOSE_DEBIT]]},   # Closing Net Price
        {'range': 'N321', 'values': [[CSP_PNL]]},           # Total PnL
        {'range': 'P321', 'values': [['Split from 430/410 BPS; short leg rolled to $425P 9/18']]},
    ], value_input_option='USER_ENTERED')
    print("✓ Row 321 converted to CLOSED CSP $430P")

    # --- 2. Insert new row (322) for the long Put $410P -------------------
    put_row = [
        "6/2/2026",          # A Opening Date
        CLOSE_DATE,          # B Closing Date
        "MSFT",              # C Underlying
        "Put",               # D Strategy Type (long put)
        "Closed",            # E Status
        "8/21/2026",         # F Expiration
        "",                  # G Short/CSP/CC Strike (none - long put)
        410,                 # H Long Strike
        "",                  # I Delta
        PUT_FEES,            # J Fees
        PUT_OPEN_DEBIT,      # K Opening Net Price (debit)
        PUT_CLOSE_CREDIT,    # L Closing Net Price (credit)
        1,                   # M Contracts
        PUT_PNL,             # N Total PnL
        "",                  # O ROC
        "Long leg of 6/2 MSFT 430/410 BPS, closed for gain",  # P Notes
    ]
    sheet.insert_row(put_row, 322, value_input_option='USER_ENTERED')

    # copy formatting (currency/number formats + alignment) from row 321 -> 322
    sid = sheet.id
    ss.batch_update({'requests': [{
        'copyPaste': {
            'source':      {'sheetId': sid, 'startRowIndex': 320, 'endRowIndex': 321,
                            'startColumnIndex': 0, 'endColumnIndex': 16},
            'destination': {'sheetId': sid, 'startRowIndex': 321, 'endRowIndex': 322,
                            'startColumnIndex': 0, 'endColumnIndex': 16},
            'pasteType': 'PASTE_FORMAT',
        }
    }]})
    print("✓ Inserted CLOSED long Put $410P at row 322 (format copied from 321)")

    print("\n=== AFTER ===")
    show(sheet, 321)
    show(sheet, 322)

    # --- 3. Clear the $410P entry from Import Errors ----------------------
    try:
        err = ss.worksheet('Import Errors')
        rows = err.get_all_values()
        deleted = False
        for i in range(len(rows) - 1, 0, -1):   # skip header
            row = rows[i]
            blob = " ".join(row)
            if 'MSFT' in blob and '410' in blob:
                err.delete_rows(i + 1)
                print(f"✓ Cleared Import Errors row {i + 1}: {row}")
                deleted = True
        if not deleted:
            print("• No matching MSFT $410P import error found (already clear)")
    except Exception as e:
        print(f"✗ Could not access Import Errors: {e}")

    print("\nReconciliation: CSP PnL {:+.2f} + Put PnL {:+.2f} = {:+.2f} realized on unwind"
          .format(CSP_PNL, PUT_PNL, CSP_PNL + PUT_PNL))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
