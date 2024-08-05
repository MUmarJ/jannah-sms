# Using streamlit, create a web app that allows the user to upload a CSV file and diplay a Pandas DataFrame:
import streamlit as st
import pandas as pd
import io
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

SMS_KEY = os.getenv("SMS_KEY")
# print(SMS_KEY)
SMS_KEY_TEST = SMS_KEY + "_test"
API_BASE = "https://textbelt.com/text"

# print(st.session_state)


# Create a Test API Key function:
def test_api_key():
    resp = requests.post(
        API_BASE,
        {
            "phone": "7737154705",
            "message": "Hello world",
            "key": SMS_KEY_TEST,
        },
    )
    print(resp.json())
    if resp.json()["success"]:
        # Display a success message in streamlit:
        st.success("Key is valid")
    else:
        # Display an error message in streamlit:
        st.error("Key is not valid")


def send_sms_df(df, test=True):
    for _, row in df.iterrows():
        if row["Send Rent SMS"]:
            send_sms(row, test)


# Loop through the DataFrame and send SMS messages to the contacts:
def send_sms(tenantRow, test=True):
    TEST_MSG = (
        f'Hello {tenantRow["Name"]}, your rent is due on {tenantRow["Due Date"]}.'
    )
    resp = requests.post(
        API_BASE,
        {
            "phone": tenantRow["Contact"],
            "message": TEST_MSG,
            "key": test and SMS_KEY_TEST or SMS_KEY,
        },
    )
    print(resp.json())
    send_notifcation = st.empty()
    if resp.json()["success"]:
        # Display a success message in streamlit:
        send_notifcation = st.success(f"SMS sent to {tenantRow['Name']}")
    else:
        # Display an error message in streamlit:
        send_notifcation = st.error(f"SMS not sent to {tenantRow['Name']}")

    time.sleep(1)
    send_notifcation.empty()


st.set_page_config(page_title="Jannah SMS Test", layout="wide")
st.title("Jannah SMS Test")


uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
    # Load the CSV file into a pandas DataFrame and display it in streamlit with Contact as strings, Rent as integers, and Due Date as dates and "Send Rent SMS" as True or False:
    df = pd.read_csv(
        uploaded_file,
        dtype={
            "Contact": str,
            "Rent": int,
            "Due Date": str,
            "Send Rent SMS": bool,
        },
    )
    # Load editable_df in streamlit session state:
    st.session_state["editable_df"] = st.data_editor(df)

st.session_state["test_api_key_button"] = st.button(
    "Test API Key", on_click=test_api_key
)

# Initialize editable_df in streamlit session state:
if "editable_df" not in st.session_state:
    st.session_state["editable_df"] = None

st.session_state["send_sms_button"] = st.button(
    "Send SMS",
    on_click=send_sms_df,
    disabled=st.session_state["editable_df"] is None,
    args=(st.session_state["editable_df"], True),
)

# Add a button to save the updated DataFrame back to the CSV file if the user has made any changes with the same name but new timestamp:

if st.session_state["editable_df"] is not None:
    if st.button("Save Updated SMS Contacts"):
        st.session_state["editable_df"].to_csv("JannahSMSTestContacts.csv", index=False)
        st.success("Changes saved to JannahSMSTestContacts.csv")
