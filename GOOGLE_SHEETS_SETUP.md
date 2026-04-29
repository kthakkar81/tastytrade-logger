# Google Sheets API Setup

To enable the spreadsheet logger to write to your Google Sheets, you need to set up a service account.

## Steps:

### 1. Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Name it something like "Tastytrade Logger"

### 2. Enable Google Sheets API
1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API"
3. Click "Enable"
4. Also enable "Google Drive API"

### 3. Create Service Account
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Name: "tastytrade-logger"
4. Click "Create and Continue"
5. Skip optional steps, click "Done"

### 4. Generate JSON Key
1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" → "Create New Key"
4. Choose "JSON" format
5. Click "Create"
6. Save the downloaded JSON file as `google-sheets-credentials.json` in your project directory

### 5. Share Spreadsheet with Service Account
1. Open the downloaded JSON file
2. Copy the `client_email` value (looks like: `tastytrade-logger@project.iam.gserviceaccount.com`)
3. Open your test spreadsheet in Google Sheets
4. Click "Share"
5. Paste the service account email
6. Give it "Editor" permissions
7. Click "Send"

**Repeat step 5 for your production spreadsheet when ready**

### 6. Install Dependencies
```bash
pip install -r requirements.txt
```

### 7. Test the Logger
```bash
python spreadsheet_logger.py
```

This will fetch transactions from 4/27/2026 and write them to your test spreadsheet.

## Security Note
- **Never commit** `google-sheets-credentials.json` to git
- It's already in `.gitignore`
- Keep this file secure as it has write access to your spreadsheets
