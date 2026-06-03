"""
Check existing row formatting in spreadsheet
"""
import gspread
from google.oauth2.service_account import Credentials
import config
import json

# Authenticate
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_file(
    config.GOOGLE_SHEETS_CREDENTIALS_FILE,
    scopes=scopes
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(config.TEST_SPREADSHEET_ID)
sheet = spreadsheet.sheet1

# Get formatting for a row with data (row 285 was mentioned)
print("Checking formatting for row 285...")

# Get cell formats for row 285
for col_letter, col_num in [('A', 1), ('B', 2), ('C', 3), ('D', 4), ('E', 5),
                              ('F', 6), ('G', 7), ('H', 8), ('I', 9), ('J', 10),
                              ('K', 11), ('L', 12), ('M', 13), ('N', 14), ('O', 15), ('P', 16)]:
    cell = sheet.cell(285, col_num, value_render_option='FORMULA')

    # Get format using get() to see full cell properties
    response = sheet.spreadsheet.values_get(f'{col_letter}285')

print("\nGetting full cell format info...")
# Get formatting using the Sheets API directly
sheet_id = sheet.id
spreadsheet_id = spreadsheet.id

# Use the underlying API client
result = client.request(
    'get',
    f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}',
    params={
        'ranges': f'{sheet.title}!A285:P285',
        'fields': 'sheets(data(rowData(values(effectiveFormat))))'
    }
)

if 'sheets' in result:
    try:
        formats = result['sheets'][0]['data'][0]['rowData'][0]['values']
        for i, cell_format in enumerate(formats):
            col_letter = chr(65 + i)  # A, B, C, etc.
            print(f"\nColumn {col_letter} ({i+1}):")
            if 'effectiveFormat' in cell_format:
                fmt = cell_format['effectiveFormat']
                if 'horizontalAlignment' in fmt:
                    print(f"  Alignment: {fmt['horizontalAlignment']}")
                if 'numberFormat' in fmt:
                    print(f"  Number format: {fmt['numberFormat']}")
    except Exception as e:
        print(f"Error parsing format: {e}")
        print(json.dumps(result, indent=2))
