from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import json
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaInMemoryUpload
import streamlit as st
import pandas as pd

class discount():

    # Connect to Google drive for JSON
    def get_drive_service():
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["connections"]["gsheets"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    
    # Read Google JSON Discount file
    @staticmethod
    def read_json_from_drive():
        file_id = st.secrets["file_address"]["JSON_FILE_ID"]
        drive_service = discount.get_drive_service()

        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        return json.load(fh)
    
    # Append existing JSON to new discount entry
    @staticmethod
    def append_discount(existing_json: dict, discount_payload: dict):
        # Defensive conversion
        if isinstance(discount_payload, str):
            discount_payload = json.loads(discount_payload)

        if not isinstance(discount_payload, dict):
            raise TypeError("discount_payload must be a dict")

        discount_type = discount_payload["discount_type"]

        # remove control key
        record = discount_payload.copy()
        record.pop("discount_type")

        # ensure list exists
        if discount_type not in existing_json:
            existing_json[discount_type] = []

        # optional: check overlapping dates
        existing_json[discount_type].append(record)

        return existing_json
    
    # Write Google JSON Discount file
    @staticmethod
    def overwrite_json_in_drive(data):
        file_id = st.secrets["file_address"]["JSON_FILE_ID"]
        drive_service = discount.get_drive_service()

        json_bytes = json.dumps(data, indent=2).encode("utf-8")

        media = MediaInMemoryUpload(
            json_bytes,
            mimetype="application/json",
            resumable=False
        )

        drive_service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()

    @staticmethod
    def display_discounts_expander(discount_json: dict):
        for discount_type, records in discount_json.items():
            with st.expander(f"{discount_type} ({len(records)} record(s))"):
                for i, record in enumerate(records, start=1):
                    # st.markdown(f"**Version {i}**")
                    cols = st.columns(len(record))
                    for col, (k, v) in zip(cols, record.items()):
                        col.metric(label=k.replace("_", " ").title(), value=v)