"""
Handle CSV and Excel file parsing
"""

import pandas as pd
import io
import base64


class FileHandler:
    """Handle CSV and Excel file parsing"""

    ALLOWED_EXTENSIONS = {'csv', 'xls', 'xlsx'}
    MAX_FILE_SIZE_MB = 50

    @staticmethod
    def parse_file(file_content, filename: str):
        """Parse uploaded file and return DataFrame

        Args:
            file_content: file.contents from dcc.Upload (base64 string)
            filename: original filename

        Returns:
            pd.DataFrame if successful
            Raises: ValueError if parsing fails
        """
        # Extract extension
        ext = filename.rsplit('.', 1)[1].lower()
        if ext not in FileHandler.ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported format. Allowed: {FileHandler.ALLOWED_EXTENSIONS}")

        try:
            # Decode base64 content
            content = file_content.split(',')[1]  # Remove "data:application/..." prefix
            decoded = io.BytesIO(base64.b64decode(content))

            # Parse based on extension
            if ext == 'csv':
                for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1'):
                    try:
                        decoded.seek(0)
                        df = pd.read_csv(decoded, encoding=encoding)
                        break
                    except (UnicodeDecodeError, Exception):
                        continue
                else:
                    raise ValueError("Could not decode file — try saving as UTF-8 CSV.")
            elif ext == 'xlsx':
                df = pd.read_excel(decoded, engine='openpyxl')
            elif ext == 'xls':
                df = pd.read_excel(decoded, engine='xlrd')

            return df

        except Exception as e:
            raise ValueError(f"Failed to parse {filename}: {str(e)}")

    @staticmethod
    def validate_dataframe(df):
        """Validate DataFrame has required structure

        Returns: (is_valid, error_message)
        """
        if df.empty:
            return False, "File is empty"
        if len(df) < 2:
            return False, "File must have at least 2 rows"
        if len(df.columns) < 2:
            return False, "File must have at least 2 columns"
        return True, None
